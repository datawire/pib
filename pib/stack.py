"""The Pibstack.yaml parsing code."""

import yaml

from .schema import validate, PIBSTACK_SCHEMA


class StackConfig(object):
    """The configuration for the stack."""

    def __init__(self, path_to_repo):
        self.components = {}
        self.path_to_repo = path_to_repo

        stack = path_to_repo / "Pibstack.yaml"
        with stack.open() as f:
            data = yaml.safe_load(f.read())
        validate(PIBSTACK_SCHEMA, data)
        self.name = data["name"]
        self.docker_repository = data["image"]["repository"]
        self.port = data["image"]["port"]
        self.expose = data.get("expose", None)
        for component in data.get("requires", []):
            name = "{}-{}".format(self.name, component["template"])
            self.components[name] = component["template"]
