"""Tests for schema module."""

import pytest

from ..schema import validate, ValidationError

TEST_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {
            "type": "string"
        },
        "count": {
            "type": "integer",
        }
    },
    "required": ["name", "count"]
}


def test_validates_good_instance():
    """
    Given an instance of the schema, `validate()` raises no error.
    """
    validate(TEST_SCHEMA, dict(name="hello", count=123))


def test_error_on_bad_instance():
    """
    A bad instances causes `validate()` to raise a `ValidationError`.
    """
    with pytest.raises(ValidationError) as e:
        validate(TEST_SCHEMA, dict(name=123))
    assert sorted(e.value.errors) == sorted([
        "/: 'count' is a required property",
        "/name: 123 is not of type 'string'"
    ])
