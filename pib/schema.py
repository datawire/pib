"""Schema for the Pibstack.yaml file.

We use JSON Schema since it has decent tooling.
"""

from jsonschema import Draft4Validator
from yaml import safe_load
from pathlib import Path

with (Path(__file__).parent / "schema.yaml").open() as f:
    PIBSTACK_SCHEMA = safe_load(f.read())


class ValidationError(Exception):
    """
    Has list of validation errors.
    """
    def __init__(self, errors):
        self.errors = errors
        Exception.__init__(self)


def validate(schema, instance):
    """
    Validate a YAML file that has been parsed into a Python object.

    :param schema: The decoded (POPO) schema.
    :param instance: The decoded (POPO) instance to validate.

    :raises ValidationError: if validation failed.
    """
    validator = Draft4Validator(schema)
    if not validator.is_valid(instance):
        errors = ["/{}: {}".format("/".join(map(str, e.path)), e.message)
                  for e in validator.iter_errors(instance)]
        raise ValidationError(errors)


__all__ = ["validate", "ValidationError"]
