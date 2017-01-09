"""Schema for the Pibstack.yaml file.

We use JSON Schema since it has decent tooling.
"""

from jsonschema import Draft4Validator
from yaml import safe_load
from pathlib import Path

with (Path(__file__).parent / "schema.yaml").open() as f:
    VALIDATOR = Draft4Validator(safe_load(f.read()))


class ValidationError(Exception):
    """
    Has list of validation errors.
    """
    def __init__(self, errors):
        self.errors = errors
        Exception.__init__(self)


def validate(pibstack):
    """
    Validate a Pibstack.yaml file that has been parsed into Python object.

    :raises ValidationError: if validation failed.
    """
    if not VALIDATOR.is_valid(pibstack):
        errors = [str(e) for e in VALIDATOR.iter_errors(pibstack)]
        raise ValidationError(errors)


__all__ = ["validate", "ValidationError"]
