"""Local operations."""

import json
import os
from os.path import expanduser
from pathlib import Path
from shutil import rmtree
from subprocess import check_call, check_output, CalledProcessError
from tempfile import NamedTemporaryFile
from time import sleep, time

from yaml import safe_load, safe_dump

from .envfile import load_env_file


PIB_DIR = Path(expanduser("~")) / ".pib"
ENV_DIR = PIB_DIR / "environments"
DEFAULT_ENV_DIR = ENV_DIR / "default"
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

COMPONENT_DEPLOYMENT = """\
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
      - name: "{name}"
        image: "{image}"
        imagePullPolicy: IfNotPresent
        ports:
        - containerPort: {port}
"""

COMPONENT_CONFIGMAP = """\
apiVersion: v1
kind: ConfigMap
metadata:
  name: "{name}-config"
data:
  host: "{name}"
  port: "{port}"
"""


def yaml_render(template, params, transform=lambda x: None):
    """Render a YAML template.

    :param template str: YAML-encoded template.
    :param params dict: Values to substitute on template.
    :param transform: Mutate the decoded YAML object.
    :return: The resulting YAML-encoded config.
    """
    # 1. Substitute values:
    loaded_config = safe_load(template.format(**params))
    # 2. Transform:
    transform(loaded_config)
    return safe_dump(loaded_config)


def run_result(command, **kwargs):
    """Return (stripped) command result as unicode string."""
    return str(check_output(command, **kwargs).strip(), "utf-8")


class RunLocal(object):
    """Context for running local operations."""

    def __init__(self, logfile):
        self.logfile = logfile

    def _check_call(self, *args, **kwargs):
        """Run a subprocess, make sure it exited with 0."""
        self.logfile.write("Running: {}\n".format(args))
        check_call(*args, stdout=self.logfile, stderr=self.logfile, **kwargs)

    def initialize_environment(self, git_path):
        """Initialize the environment, by doing a git clone."""
        if not ENV_DIR.exists():
            os.makedirs(str(ENV_DIR))
        if DEFAULT_ENV_DIR.exists():
            rmtree(str(DEFAULT_ENV_DIR))
        self._check_call(["git", "clone", git_path, "default"],
                         cwd=str(ENV_DIR))

    def update_environment(self):
        """Update the environment checkout."""
        if DEFAULT_ENV_DIR.exists():
            self._check_call(["git", "pull"], cwd=str(DEFAULT_ENV_DIR))

    def get_envfile(self):
        """Load the Envfile.yaml, if any.

        :return: Object that has YAML keys as attributes, or None if there is
            no Envfile.yaml.
        """
        if (DEFAULT_ENV_DIR / "Envfile.yaml").exists():
            return load_env_file(DEFAULT_ENV_DIR)
        else:
            return None

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

    def _kubectl(self, command, config, kubectl_args=[]):
        """Run kubectl.

        :param command: The kubectl command.
        :param params: Parameters with which to render the configs.
        :param configs: YAML-encoded configuration.
        """
        with NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
            f.write(config)
            f.flush()
            self._check_call([str(KUBECTL), command, "-f", f.name] +
                             kubectl_args)

    def _kubectl_apply(self, config):
        """Run kubectl apply on the given configs."""
        self._kubectl("apply", config)

    def _kubectl_delete(self, config):
        """Run kubectl delete on the given configs."""
        self._kubectl("delete", config,
                      kubectl_args=["--ignore-not-found=true"])

    def wipe(self):
        """Delete everything from k8s."""
        for category in ["ingress", "service", "deployment", "pod"]:
            self._check_call([str(KUBECTL), "delete", category, "--all"])

    def rebuild_docker_image(self, stack_config):
        """Rebuild the Docker image for current directory.

        :return dict: map application name to tag to use.
        """
        app_name = stack_config.stack.name
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
                              stack_config.stack.image.repository, tag)])
        return tag_overrides

    def deploy(self, stack_config, tag_overrides):
        """Deploy current configuration to the minikube server."""
        self._deploy_service(stack_config.stack, tag_overrides)
        self._deploy_components(stack_config.stack)

    def _component_name(self, stack, component):
        return "{}-{}".format(stack.name, component.template)

    def _deploy_service(self, stack, tag_overrides):
        name = stack.name
        params = dict(name=name)
        params["port"] = stack.image.port
        params["image"] = stack.image.repository
        params["service_type"] = "NodePort"
        params["tag"] = tag_overrides.get(name, "latest")
        self._kubectl_apply(yaml_render(SERVICE, params))
        self._kubectl_apply(yaml_render(COMPONENT_CONFIGMAP, params))

        def add_environment(deployment_config):
            env = []
            for component in stack.requires:
                for value in ["host", "port"]:
                    env.append({
                        "name": "{}_COMPONENT_{}".format(
                            component.template.upper().replace("-", "_"),
                            value.upper()),
                        "valueFrom": {
                            "configMapKeyRef":
                            {"name": "{}-config".format(
                                self._component_name(stack, component)),
                             "key": value}}
                    })
            deployment_config["spec"]["template"]["spec"]["containers"][0][
                "env"] = env
        self._kubectl_apply(yaml_render(HTTP_DEPLOYMENT, params,
                                        transform=add_environment))
        if stack.expose:
            params["path"] = stack.expose.path
            self._kubectl_apply(yaml_render(INGRESS, params))
        else:
            # Remove any existing ingress:
            params["path"] = "/"
            self._kubectl_delete(yaml_render(INGRESS, params))

    def _deploy_components(self, stack):
        envfile = self.get_envfile()

        def get_overrides(component_template):
            if envfile is None:
                return None
            try:
                return getattr(envfile.environments.local.components,
                               component_template)
            except KeyError:
                return None

        for component in stack.requires:
            params = {}
            params["name"] = self._component_name(stack, component)
            overrides = get_overrides(component.template)
            source_of_truth = component
            if overrides is not None:
                source_of_truth = overrides
            params["port"] = source_of_truth.config.port
            params["image"] = source_of_truth.image
            params["service_type"] = "ClusterIP"
            for k8sobj in [SERVICE, COMPONENT_DEPLOYMENT, COMPONENT_CONFIGMAP]:
                self._kubectl_apply(yaml_render(k8sobj, params))

    def get_service_url(self, stack_config):
        """Return service URL as string."""
        name = stack_config.stack.name
        try:
            ingress_status = json.loads(run_result(
                [str(KUBECTL), "get", "ingress",
                 name + "-ingress", "-o", "json"]))
            host = ingress_status["status"]["loadBalancer"]["ingress"][0]["ip"]
            path = ingress_status["spec"]["rules"][0]["http"][
                "paths"][0]["path"]
            return "http://{}{}".format(host, path)
        except CalledProcessError:
            return run_result(
                [str(MINIKUBE), "service", "--url", name])

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
