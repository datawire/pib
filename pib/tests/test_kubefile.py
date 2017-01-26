"""Tests for pib.envfile."""

import pytest
from yaml import safe_load

from ..schema import ValidationError
from ..kubefile import (load_kubefile, Cluster, System, MasterConfig, NodesConfig)


def test_load_invalid_instance():
    """
    Loading invalid instance of the Envfile.yaml schema raises an exception.
    """
    with pytest.raises(ValidationError):
        load_kubefile({"not": "valid"})

INSTANCE = """
---
Kubefile-version: 1
cluster:
    master:
        size: t2.medium
    nodes:
        size: t2.large
        count: 5
"""


def test_load_valid_instance():
    instance = safe_load(INSTANCE)
    assert load_kubefile(instance) == System(
        cluster=Cluster(
            master=MasterConfig(size='t2.medium'),
            nodes=NodesConfig(size='t2.large', count=5)
        )
    )
