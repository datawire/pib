"""Local interactions with Minikube and friends."""

import os
from os.path import expanduser
from pathlib import Path
from subprocess import CalledProcessError
from time import sleep, time

from .kubernetes import envfile_to_k8s, RenderingOptions
from .kubectl import Kubectl
from .subprocesses import Runner

PIB_DIR = Path(expanduser("~")) / ".pib"
MINIKUBE = PIB_DIR / "minikube"
KUBECTL = PIB_DIR / "kubectl"


class RunLocal(object):
    """Context for running local operations."""

    def __init__(self, logfile, echo):
        """
        :param logfile: file-like object to write logs to.
        :param echo: callable to write user output to. Presumed to add
            linebreaks.
        """
        self._runner = Runner(logfile)
        self._kubectl = Kubectl(self._runner, KUBECTL, "minikube")
        self._echo = echo

    def ensure_requirements(self):
        """Make sure kubectl and minikube are available."""
        uname = self._runner.get_output("uname").lower()
        for path, url in zip([MINIKUBE, KUBECTL], [
                "https://storage.googleapis.com/minikube/releases/"
                "v0.15.0/minikube-{}-amd64",
                "https://storage.googleapis.com/kubernetes-release/"
                "release/v1.5.1/bin/{}/amd64/kubectl"
        ]):
            if path.exists() and not os.access(str(path), os.X_OK):
                # Apparently failed halfway through previous download
                os.remove(str(path))
            if not path.exists():
                self._echo("Downloading {}...".format(path.name))
                self._runner.check_call([
                    "curl", "--create-dirs", "--silent", "--output", str(path),
                    url.format(uname)
                ])
                path.chmod(0o755)

    def start_minikube(self):
        """Start minikube."""
        running = True
        try:
            result = self._runner.get_output([str(MINIKUBE), "status"])
            running = "Running" in result
        except CalledProcessError:
            running = False
        if not running:
            self._echo("Starting minikube...")
            self._runner.check_call([str(MINIKUBE), "start"])
            self._runner.check_call(
                [str(MINIKUBE), "addons", "enable", "ingress"])
            sleep(10)  # make sure it's really up

    def wipe(self):
        """Delete everything from k8s."""
        for category in ["ingress", "service", "deployment", "pod"]:
            self._kubectl.run(["delete", category, "--all"])

    def _rebuild_docker_image(self, docker_image, directory):
        """Rebuild the Docker image for a particular service.

        :param docker_image DockerImage: Docker image name to use.
        :param directory Path: Directory where the `Dockerfile` can be found.

        :return str: the Docker tag to use.
        """
        tag = self._runner.get_output(
            ["git", "describe", "--tags", "--dirty", "--always", "--long"],
            cwd=str(directory)) + "-" + str(time())
        self._runner.check_call([
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
                self._echo("Service {} found in {}, rebuilding Docker"
                           " image with latest code...".format(
                               name, services_directory.absolute()))
                tag_overrides[name] = self._rebuild_docker_image(service.image,
                                                                 subdir)
            else:
                # Otherwise, use tag in Envfile.yaml:
                # By default use the tag in the Envfile.yaml:
                self._echo(
                    "Service {} not found in {}, using tag '{}'"
                    " from Envfile.yaml.".format(name,
                                                 services_directory.absolute(),
                                                 service.image.tag))
        return tag_overrides

    def deploy(self, envfile, tag_overrides={}):
        """Deploy current configuration to the minikube server."""
        # TODO: missing ability to remove previous iteration of k8s objects!
        options = RenderingOptions(tag_overrides=tag_overrides,
                                   # Make services publicly available:
                                   private_service_type="NodePort")
        for k8s_config in envfile_to_k8s(envfile):
            self._kubectl.apply_config(k8s_config.render(options))

    def get_application_urls(self, envfile):
        """
        :return: Tuple of service URLs as {name: url} and the main URL.
        """
        return {
            service_name: self._runner.get_output(
                [str(MINIKUBE), "service", "--url", service_name])
            for service_name in envfile.application.services
        }, "http://{}/".format(self._runner.get_output([str(MINIKUBE), "ip"]))

    def set_minikube_docker_env(self):
        """Use minikube's Docker."""
        shell_script = self._runner.get_output(
            [str(MINIKUBE), "docker-env", "--shell", "bash"])
        for line in shell_script.splitlines():
            line = line.strip()
            if line.startswith("#"):
                continue
            if line.startswith("export "):
                key, value = line[len("export "):].strip().split("=", 1)
                value = value.strip('"')
                os.environ[key] = value
