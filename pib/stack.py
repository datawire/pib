"""The Pibstack.yaml parsing code."""

import yaml
import python_jsonschema_objects as pjs

from .schema import validate, PIBSTACK_SCHEMA

Pibstack = pjs.ObjectBuilder(PIBSTACK_SCHEMA).build_classes().Pibstack


class StackConfig(object):
    """The configuration for the stack."""

    def __init__(self, path_to_repo):
        self.components = {}
        self.path_to_repo = path_to_repo

        stack = path_to_repo / "Pibstack.yaml"
        with stack.open() as f:
            data = yaml.safe_load(f.read())
        validate(PIBSTACK_SCHEMA, data)
        self.stack = Pibstack(**data)
