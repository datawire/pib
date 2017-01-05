#!/usr/bin/env python3

from pathlib import Path
from subprocess import run, PIPE, CalledProcessError
from tempfile import NamedTemporaryFile
from os.path import expanduser
from time import sleep
from random import random
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
        # We put random value in to force redeploy:
        random: "{random}"
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


def ensure_requirements():
    """Make sure kubectl and minikube are available."""
    uname = str(run(["uname"], stdout=PIPE, check=True).stdout.lower().strip(),
                "utf-8")
    for path, url in zip(
            [MINIKUBE, KUBECTL],
            ["https://storage.googleapis.com/minikube/releases/"
             "v0.13.1/minikube-{}-amd64",
             "https://storage.googleapis.com/kubernetes-release/"
             "release/v1.4.0/bin/{}/amd64/kubectl"]):
        if not path.exists():
            run(["curl",
                 "--create-dirs",
                 "--silent",
                 "--output", str(path),
                 url.format(uname)])
            path.chmod(0o755)


def start_minikube():
    """Start minikube."""
    try:
        run([str(MINIKUBE), "status"], check=True)
    except CalledProcessError:
        run([str(MINIKUBE), "start"])
        sleep(10)  # make sure it's really up


def kubectl(params, configs):
    """Run kubectl on the given configs."""
    for config in configs:
        config = config.format(**params)
        with NamedTemporaryFile("w", suffix=".yaml") as f:
            f.write(config)
            f.flush()
            run([str(KUBECTL), "apply", "-f", f.name], check=True)


def deploy(data, tag_overrides):
    """Deploy current configuration to the minikube server."""
    for service in data:
        params = dict(name=service["name"],
                      random=random())
        if service["type"] == "service":
            params["port"] = service.get("port", 80)
            params["image"] = service["image"]
            params["service_type"] = "NodePort"
            params["tag"] = tag_overrides.get(service["name"], "latest")
            kubectl(params, [SERVICE, HTTP_DEPLOYMENT])
        elif service["type"] == "postgres":
            params["port"] = 5432
            params["service_type"] = "ClusterIP"
            kubectl(params, [SERVICE, POSTGRES_DEPLOYMENT])


def main(tag_overrides):
    """Start minikube and deploy current config."""
    ensure_requirements()
    start_minikube()
    stacks = Path("stacks")
    for stack in stacks.iterdir():
        data = yaml.safe_load(stack.read_text())
        deploy(data, tag_overrides)
    run([str(MINIKUBE), "service", "list", "--namespace=default"])


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("""\
Usage: pib.py deploy [name=version ...]
       pib.py status
""")
        sys.exit(1)
    if sys.argv[1] == "deploy":
        main(dict([s.split("=") for s in sys.argv[2:]]))
    else:
        raise SystemExit("Not implemented yet.")
