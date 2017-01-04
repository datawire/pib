#!/usr/bin/env python3

from pathlib import Path

import yaml


SERVICE = """"
apiVersion: v1
kind: Service
metadata:
  name: {name}
  labels:
    name: {name}
spec:
  type: {service_type}
  ports:
  - port: {external_port}
    targetPort: {internal_port}
    protocol: TCP
    name: {name}
  selector:
    name: {name}
"""


HTTP_DEPLOYMENT = """
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
        image: "{image}:latest"
        imagePullPolicy: Always
        ports:
        - containerPort: {port}
        livenessProbe:
          httpGet:
            path: /
            port: "{port}"
        readinessProbe:
          httpGet:
            path: /
            port: "{port}"
        env: {env}
"""


POSTGRES_DEPLOYMENT = """
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


def start_minikube():
    """Start minikube."""


def deploy(data):
    """Deploy current configuration to the minikube server."""
    for service in data:
        params = dict(name=service["name"])
        if service["type"] == "service":
            params["port"] = 80
            params["service_type"] = "NodePort"
            kubectl(params, [SERVICE, HTTP_DEPLOYMENT])
        elif service["type"] == "postgres":
            params["port"] = 5432
            params["service_type"] = "ClusterIP"
            kubectl(params, [SERVICE, POSTGRES_DEPLOYMENT])


def main():
    """Start minikube and deploy current config."""
    stacks = Path("stacks")
    for stack in stacks.iterdir():
        data = yaml.safe_read(stack.read_text())
        deploy(data)
