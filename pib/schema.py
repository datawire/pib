"""Schema for the Envfile.yaml file.

We use JSON Schema since it has decent tooling.
"""

from pathlib import Path

from jsonschema import Draft4Validator
from yaml import safe_load

with (Path(__file__).parent / "envfile-schema.yaml").open() as f:
    ENVFILE_SCHEMA = safe_load(f.read())

with (Path(__file__).parent / "kubefile-schema.yaml").open() as f:
    KUBEFILE_SCHEMA = safe_load(f.read())


class ValidationError(Exception):
    """
    Has list of validation errors.
    """

    def __init__(self, errors):
        self.errors = errors
        Exception.__init__(self)

    def __str__(self):
        return "Errors:" + "\n".join(self.errors)


def validate(schema, instance):
    """
    Validate a YAML file that has been parsed into a Python object.

    :param schema: The decoded (POPO) schema.
    :param instance: The decoded (POPO) instance to validate.

    :raises ValidationError: if validation failed.
    """
    validator = Draft4Validator(schema)
    if not validator.is_valid(instance):
        errors = []
        for e in validator.iter_errors(instance):
            message = e.message
            # Better error messages, workaround for
            # https://github.com/Julian/jsonschema/issues/316:
            if (e.validator == "additionalProperties" and
                    not e.validator_value and "patternProperties" in e.schema):
                for key in e.instance.keys():
                    if repr(key) in e.message:
                        message = (
                            "{} does not match any of these "
                            "regexs: {}.".format(
                                repr(key),
                                ", ".join(e.schema["patternProperties"].keys())))
                        break
            errors.append(
                "/{}: {}".format("/".join(map(str, e.path)), message))
        raise ValidationError(errors)


__all__ = ["validate", "ValidationError"]
