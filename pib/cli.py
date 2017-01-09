#!/usr/bin/env python3

from pathlib import Path
from subprocess import check_output, check_call, CalledProcessError
from tempfile import NamedTemporaryFile
from os.path import expanduser
from time import sleep, time
import os
import sys

import yaml

PIB_DIR = Path(expanduser("~")) / ".pib"
MINIKUBE = PIB_DIR / "minikube"
KUBECTL = PIB_DIR / "kubectl"


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
    name: {name}
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
  replicas: 1
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
        livenessProbe:
          httpGet:
            path: /
            port: {port}
        readinessProbe:
          httpGet:
            path: /
            port: {port}
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


def ensure_requirements():
    """Make sure kubectl and minikube are available."""
    uname = run_result("uname").lower()
    for path, url in zip(
            [MINIKUBE, KUBECTL],
            ["https://storage.googleapis.com/minikube/releases/"
             "v0.14.0/minikube-{}-amd64",
             "https://storage.googleapis.com/kubernetes-release/"
             "release/v1.5.1/bin/{}/amd64/kubectl"]):
        if not path.exists():
            check_call(["curl",
                        "--create-dirs",
                        "--silent",
                        "--output", str(path),
                        url.format(uname)])
            path.chmod(0o755)


def start_minikube():
    """Start minikube."""
    running = True
    try:
        result = run_result([str(MINIKUBE), "status"])
        running = "Running" in result
    except CalledProcessError:
        running = False
    if not running:
        check_call([str(MINIKUBE), "start"])
        sleep(10)  # make sure it's really up


def kubectl(params, configs):
    """Run kubectl on the given configs."""
    for config in configs:
        config = config.format(**params)
        with NamedTemporaryFile("w", suffix=".yaml") as f:
            f.write(config)
            f.flush()
            check_call([str(KUBECTL), "apply", "-f", f.name])


class StackConfig(object):
    """The configuration for the stack."""

    def __init__(self, path_to_repo):
        self.services = {}   # map service name to config dict
        self.databases = {}  # map database name to config dict
        stack = path_to_repo / "Pibstack.yaml"
        with stack.open() as f:
            data = yaml.safe_load(f.read())
        self.name = data["main"]["name"]
        for service in [data["main"]] + data["requires"]:
            name = service["name"]
            if service["type"] == "service":
                self.services[name] = service
            elif service["type"] == "postgres":
                self.databases[name] = service
            else:
                raise ValueError("Unknown type: " + service["type"])

    def deploy(self, tag_overrides):
        """Deploy current configuration to the minikube server."""
        for name, service in self.services.items():
            params = dict(name=name)
            params["port"] = service.get("port", 80)
            params["image"] = service["image"]
            params["service_type"] = "NodePort"
            params["tag"] = tag_overrides.get(service["name"], "latest")
            kubectl(params, [SERVICE, HTTP_DEPLOYMENT])
        for name, service in self.databases.items():
            params = dict(name=name)
            params["port"] = 5432
            params["service_type"] = "ClusterIP"
            kubectl(params, [SERVICE, POSTGRES_DEPLOYMENT])


def deploy(stack_config, tag_overrides):
    """Start minikube and deploy current config."""
    ensure_requirements()
    start_minikube()
    stack_config.deploy(tag_overrides)
    check_call([str(MINIKUBE), "service", "list", "--namespace=default"])


def set_minikube_docker_env():
    """Use minikube's Docker."""
    shell_script = run_result([str(MINIKUBE), "docker-env", "--shell", "bash"])
    for line in shell_script.splitlines():
        line = line.strip()
        if line.startswith("#"):
            continue
        if line.startswith("export "):
            key, value = line[len("export "):].strip().split("=", 1)
            value = value.strip('"')
            os.environ[key] = value


def watch(stack_config):
    """
    As code changes, rebuild Docker images for given repos in minikube Docker,
    then redeploy.
    """
    ensure_requirements()
    start_minikube()
    set_minikube_docker_env()
    while True:
        app_name = stack_config.name
        tag_overrides = {}
        # 1. Rebuild Docker images inside Minikube Docker process:
        tag = run_result(["git", "describe", "--tags", "--dirty",
                          "--always", "--long"]) + "-" + str(time())
        tag_overrides[app_name] = tag
        check_call(["docker", "build", ".",
                    "-t", "{}:{}".format(
                        stack_config.services[app_name]["image"], tag)])
        # 2. Redeploy
        stack_config.deploy(tag_overrides)
        # 3. Sleep a bit
        sleep(20)


USAGE = """\
Usage: pib deploy [name=image-tag ...]
       pib watch
       pib --help

Make sure you are in same directory as a Pibstack.yaml file.
"""


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print(USAGE, file=sys.stderr)
        sys.exit(1)
    if sys.argv[1] == "--help":
        print(USAGE, file=sys.stderr)
        sys.exit(0)
    stack_config = StackConfig(Path("."))
    if sys.argv[1] == "deploy":
        deploy(stack_config, dict([s.split("=", 1) for s in sys.argv[2:]]))
    elif sys.argv[1] == "watch":
        watch(stack_config)
    else:
        raise SystemExit("Not implemented yet.")
