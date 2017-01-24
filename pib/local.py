"""Local interactions with Minikube and friends."""

import os
from os.path import expanduser
from pathlib import Path
from subprocess import check_call, check_output, CalledProcessError
from tempfile import NamedTemporaryFile
from time import sleep, time

from yaml import safe_load, safe_dump

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

    def ensure_requirements(self):
        """Make sure kubectl and minikube are available."""
        uname = run_result("uname").lower()
        for path, url in zip([MINIKUBE, KUBECTL], [
                "https://storage.googleapis.com/minikube/releases/"
                "v0.15.0/minikube-{}-amd64",
                "https://storage.googleapis.com/kubernetes-release/"
                "release/v1.5.1/bin/{}/amd64/kubectl"
        ]):
            if not path.exists():
                check_call([
                    "curl", "--create-dirs", "--silent", "--output", str(path),
                    url.format(uname)
                ])
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
        self._kubectl(
            "delete", config, kubectl_args=["--ignore-not-found=true"])

    def wipe(self):
        """Delete everything from k8s."""
        for category in ["ingress", "service", "deployment", "pod"]:
            self._check_call([str(KUBECTL), "delete", category, "--all"])

    def _rebuild_docker_image(self, docker_image, directory):
        """Rebuild the Docker image for a particular service.

        :param docker_image DockerImage: Docker image name to use.
        :param directory Path: Directory where the `Dockerfile` can be found.

        :return str: the Docker tag to use.
        """
        # 1. Rebuild Docker images inside Minikube Docker process:
        tag = run_result(
            ["git", "describe", "--tags", "--dirty", "--always", "--long"],
            cwd=str(directory)) + "-" + str(time())
        self._check_call([
            "docker", "build", str(directory), "-t",
            "{}:{}".format(docker_image.repository, tag)
        ])
        return tag

    def rebuild_docker_images(self, envfile, services_directory):
        """Rebuild the Docker images for all local services.

        :return dict: map service name to tag to use.
        """
        tag_overrides = {}
        for service in envfile.application.services.values():
            name = service.name
            # If we have local checkout use local code:
            subdir = services_directory / name
            if subdir.exists():
                tag_overrides[name] = self._rebuild_docker_image(service.image,
                                                                 subdir)
            else:
                # Otherwise, use tag in Envfile.yaml:
                # By default use the tag in the Envfile.yaml:
                tag_overrides[name] = service.image.tag
        return tag_overrides

    def deploy(self, envfile, tag_overrides):
        """Deploy current configuration to the minikube server."""
        for service in envfile.application.services.values():
            self._deploy_service(service, envfile.application.requires,
                                 tag_overrides)
        self._deploy_components(envfile)

    def _deploy_service(self, service, common_requires, tag_overrides):
        """
        :param service envfile.Service: service to deploy.
        """
        name = service.name
        params = dict(name=name)
        params["port"] = service.port
        params["image"] = service.image.repository
        params["service_type"] = "NodePort"
        params["tag"] = tag_overrides.get(name, "latest")
        self._kubectl_apply(yaml_render(SERVICE, params))
        self._kubectl_apply(yaml_render(COMPONENT_CONFIGMAP, params))

        def add_env_variables(deployment_config):
            env = []
            for component in (
                    service.requires.values() + common_requires.values()):
                for value in ["host", "port"]:
                    env.append({
                        "name": "{}_COMPONENT_{}".format(
                            component.name.upper().replace("-", "_"),
                            value.upper()),
                        "valueFrom": {
                            "configMapKeyRef": {
                                "name": "{}-config".format(component.name),
                                "key": value
                            }
                        }
                    })
            deployment_config["spec"]["template"]["spec"]["containers"][0][
                "env"] = env

        self._kubectl_apply(
            yaml_render(
                HTTP_DEPLOYMENT, params, transform=add_env_variables))
        if service.expose is not None:
            params["path"] = service.expose.path
            self._kubectl_apply(yaml_render(INGRESS, params))
        else:
            # Remove any existing ingress:
            params["path"] = "/"
            self._kubectl_delete(yaml_render(INGRESS, params))

    def _deploy_components(self, envfile):
        required = list(envfile.application.requires.values()) + sum(
            [list(service.requires.values()) for service in envfile.application.services.values()], [])
        # TODO: private components can have name conflicts!
        for requirement in required:
            component = envfile.local.templates[requirement.template]
            params = {}
            params["name"] = requirement.name
            params["port"] = component.port
            params["image"] = component.image
            params["service_type"] = "ClusterIP"
            for k8sobj in [SERVICE, COMPONENT_DEPLOYMENT, COMPONENT_CONFIGMAP]:
                self._kubectl_apply(yaml_render(k8sobj, params))

    def get_application_urls(self, envfile):
        """
        :return: Tuple of service URLs as {name: url} and the main URL.
        """
        return {
            service_name:
            run_result([str(MINIKUBE), "service", "--url", service_name])
            for service_name in envfile.application.services
        }, "http://{}/".format(run_result([str(MINIKUBE), "ip"]))

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
