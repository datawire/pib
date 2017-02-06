"""Local interactions with Minikube and friends."""

import os
from os.path import expanduser
from pathlib import Path
from subprocess import check_call, check_output, CalledProcessError
from tempfile import NamedTemporaryFile
from time import sleep, time
from .kubernetes import envfile_to_k8s, RenderingOptions

from yaml import safe_dump


PIB_DIR = Path(expanduser("~")) / ".pib"
MINIKUBE = PIB_DIR / "minikube"
KUBECTL = PIB_DIR / "kubectl"


def run_result(command, **kwargs):
    """Return (stripped) command result as unicode string."""
    return str(check_output(command, **kwargs).strip(), "utf-8")


class RunLocal(object):
    """Context for running local operations."""

    def __init__(self, logfile, echo):
        """
        :param logfile: file-like object to write logs to.
        :param echo: callable to write user output to. Presumed to add
            linebreaks.
        """
        self.logfile = logfile
        self.echo = echo

    def _check_call(self, *args, **kwargs):
        """Run a subprocess, make sure it exited with 0."""
        self.logfile.write("Running: {}\n".format(args))
        self.logfile.flush()
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
            if path.exists() and not os.access(str(path), os.X_OK):
                # Apparently failed halfway through previous download
                os.remove(str(path))
            if not path.exists():
                self.echo("Downloading {}...".format(path.name))
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
            self.echo("Starting minikube...")
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
            self._check_call([str(KUBECTL), "--context=minikube", command,
                              "-f", f.name] + kubectl_args)

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
            self._check_call([str(KUBECTL), "--context=minikube",
                              "delete", category, "--all"])

    def _rebuild_docker_image(self, docker_image, directory):
        """Rebuild the Docker image for a particular service.

        :param docker_image DockerImage: Docker image name to use.
        :param directory Path: Directory where the `Dockerfile` can be found.

        :return str: the Docker tag to use.
        """
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
                self.echo("Service {} found in {}, rebuilding Docker"
                          " image with latest code...".format(
                              name, services_directory.absolute()))
                tag_overrides[name] = self._rebuild_docker_image(service.image,
                                                                 subdir)
            else:
                # Otherwise, use tag in Envfile.yaml:
                # By default use the tag in the Envfile.yaml:
                self.echo("Service {} not found in {}, using tag '{}'"
                          " from Envfile.yaml.".format(
                              name, services_directory.absolute(),
                              service.image.tag))
        return tag_overrides

    def deploy(self, envfile, tag_overrides={}):
        """Deploy current configuration to the minikube server."""
        # TODO: missing ability to remove previous iteration of k8s objects!
        options = RenderingOptions(tag_overrides=tag_overrides)
        for k8s_config in envfile_to_k8s(envfile):
            self._kubectl_apply(safe_dump(k8s_config.render(options)))

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
