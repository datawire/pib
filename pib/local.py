"""Local operations."""

import json
import os
from os.path import expanduser
from pathlib import Path
from subprocess import check_call, check_output, CalledProcessError
from tempfile import NamedTemporaryFile
from time import sleep, time


PIB_DIR = Path(expanduser("~")) / ".pib"
MINIKUBE = PIB_DIR / "minikube"
KUBECTL = PIB_DIR / "kubectl"


INGRESS = """\
apiVersion: extensions/v1beta1
kind: Ingress
metadata:
  name: {name}-ingress
spec:
  rules:
  - http:
      paths:
      - path: {path}
        backend:
          serviceName: {name}
          servicePort: {port}
"""

SERVICE = """\
apiVersion: v1
kind: Service
metadata:
  name: {name}
  labels:
    name: {name}
spec:
  type: {service_type}
  ports:
  - port: {port}
    targetPort: {port}
    protocol: TCP
  selector:
    name: {name}
"""


HTTP_DEPLOYMENT = """\
apiVersion: extensions/v1beta1
kind: Deployment
metadata:
  name: "{name}"
  labels:
    name: "{name}"
spec:
  replicas: 2
  template:
    metadata:
      labels:
        name: "{name}"
    spec:
      containers:
      - name: {name}
        image: "{image}:{tag}"
        imagePullPolicy: IfNotPresent
        ports:
        - containerPort: {port}
"""


POSTGRES_DEPLOYMENT = """\
apiVersion: extensions/v1beta1
kind: Deployment
metadata:
  name: "{name}"
  labels:
    name: "{name}"
spec:
  replicas: 1
  template:
    metadata:
      labels:
        name: "{name}"
    spec:
      containers:
      - name: {name}
        image: "postgres:9.6"
        imagePullPolicy: IfNotPresent
        ports:
        - containerPort: 5432
"""


def run_result(command, **kwargs):
    """Return (stripped) command result as unicode string."""
    return str(check_output(command, **kwargs).strip(), "utf-8")


class RunLocal(object):
    """Context for running local operations."""

    def __init__(self, logfile):
        self.logfile = logfile

    def _check_call(self, *args, **kwargs):
        """Run a subprocess, make sure it exited with 0."""
        self.logfile.write("Running: {}".format(args))
        check_call(*args, stdout=self.logfile, **kwargs)

    def ensure_requirements(self):
        """Make sure kubectl and minikube are available."""
        uname = run_result("uname").lower()
        for path, url in zip(
                [MINIKUBE, KUBECTL],
                ["https://storage.googleapis.com/minikube/releases/"
                 "v0.15.0/minikube-{}-amd64",
                 "https://storage.googleapis.com/kubernetes-release/"
                 "release/v1.5.1/bin/{}/amd64/kubectl"]):
            if not path.exists():
                check_call(["curl",
                            "--create-dirs",
                            "--silent",
                            "--output", str(path),
                            url.format(uname)])
                path.chmod(0o755)

    def start_minikube(self):
        """Start minikube."""
        running = True
        try:
            result = run_result([str(MINIKUBE), "status"])
            running = "Running" in result
        except CalledProcessError:
            running = False
        if not running:
            self._check_call([str(MINIKUBE), "start"])
            self._check_call([str(MINIKUBE), "addons", "enable", "ingress"])
            sleep(10)  # make sure it's really up

    def _kubectl(self, command, params, configs, kubectl_args=[]):
        """Run kubectl.

        :param command: The kubectl command.
        :param params: Parameters with which to render the configs.
        :param configs: YAML-encoded configuration.
        """
        for config in configs:
            config = config.format(**params)
            with NamedTemporaryFile("w", suffix=".yaml") as f:
                f.write(config)
                f.flush()
                self._check_call([str(KUBECTL), command, "-f", f.name]
                                 + kubectl_args)

    def _kubectl_apply(self, params, configs):
        """Run kubectl apply on the given configs."""
        self._kubectl("apply", params, configs)

    def _kubectl_delete(self, params, configs):
        """Run kubectl delete on the given configs."""
        self._kubectl("delete", params, configs,
                      kubectl_args=["--ignore-not-found=true"])

    def rebuild_docker_image(self, stack_config):
        """Rebuild the Docker image for current directory.

        :return dict: map application name to tag to use.
        """
        app_name = stack_config.name
        tag_overrides = {}
        # 1. Rebuild Docker images inside Minikube Docker process:
        tag = run_result(
            ["git", "describe", "--tags", "--dirty",
             "--always", "--long"],
            cwd=str(stack_config.path_to_repo)
        ) + "-" + str(time())
        tag_overrides[app_name] = tag
        self._check_call(["docker", "build", str(stack_config.path_to_repo),
                          "-t", "{}:{}".format(
                              stack_config.services[app_name]["image"], tag)])
        return tag_overrides

    def deploy(self, stack_config, tag_overrides):
        """Deploy current configuration to the minikube server."""
        for name, service in stack_config.services.items():
            params = dict(name=name)
            params["port"] = service.get("port", 80)
            params["image"] = service["image"]
            params["service_type"] = "NodePort"
            params["tag"] = tag_overrides.get(service["name"], "latest")
            self._kubectl_apply(params, [SERVICE, HTTP_DEPLOYMENT])
            if "path" in service:
                params["path"] = service["path"]
                self._kubectl_apply(params, [INGRESS])
            else:
                # Remove any existing ingress:
                params["path"] = "/"
                self._kubectl_delete(params, [INGRESS])
        for name, service in stack_config.databases.items():
            params = dict(name=name)
            params["port"] = 5432
            params["service_type"] = "ClusterIP"
            self._kubectl_apply(params, [SERVICE, POSTGRES_DEPLOYMENT])

    def get_service_url(self, stack_config):
        """Return service URL as string."""
        try:
            ingress_status = json.loads(run_result(
                [str(KUBECTL), "get", "ingress",
                 stack_config.name + "-ingress", "-o", "json"]))
            host = ingress_status["status"]["loadBalancer"]["ingress"][0]["ip"]
            path = ingress_status["spec"]["rules"][0]["http"][
                "paths"][0]["path"]
            return "http://{}{}".format(host, path)
        except CalledProcessError:
            return run_result(
                [str(MINIKUBE), "service", "--url", stack_config.name])

    def set_minikube_docker_env(self):
        """Use minikube's Docker."""
        shell_script = run_result(
            [str(MINIKUBE), "docker-env", "--shell", "bash"])
        for line in shell_script.splitlines():
            line = line.strip()
            if line.startswith("#"):
                continue
            if line.startswith("export "):
                key, value = line[len("export "):].strip().split("=", 1)
                value = value.strip('"')
                os.environ[key] = value
