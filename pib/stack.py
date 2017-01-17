"""The Pibstack.yaml parsing code."""

import yaml

from .schema import validate


class StackConfig(object):
    """The configuration for the stack."""

    def __init__(self, path_to_repo):
        self.services = {}   # map service name to config dict
        self.databases = {}  # map database name to config dict
        self.path_to_repo = path_to_repo

        stack = path_to_repo / "Pibstack.yaml"
        with stack.open() as f:
            data = yaml.safe_load(f.read())
        validate(data)
        self.name = data["main"]["name"]
        for service in [data["main"]] + data["requires"]:
            name = service["name"]
            if service["type"] == "service":
                self.services[name] = service
            elif service["type"] == "postgres":
                self.databases[name] = service
            else:
                raise ValueError("Unknown type: " + service["type"])
