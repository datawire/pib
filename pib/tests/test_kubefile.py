"""Tests for pib.envfile."""

import pytest

from ..schema import ValidationError
from ..kubefile import (load_kubefile, Cluster)


def test_load_invalid_instance():
    """
    Loading invalid instance of the Envfile.yaml schema raises an exception.
    """
    with pytest.raises(ValidationError):
        load_kubefile({"not": "valid"})

