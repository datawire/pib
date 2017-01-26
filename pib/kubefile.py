"""Code for parsing the Envfile."""

from pyrsistent import (PClass, field, pmap_field, freeze, ny as match_any,
                        discard)

from .schema import validate, KUBEFILE_SCHEMA, ValidationError


class MasterConfig(PClass):
    size = field(mandatory=True, type=str)


class NodesConfig(PClass):
    size = field(mandatory=True, type=str)
    count = field(mandatory=True, type=int)


class Cluster(PClass):
    """Represents basic cluster config parameters for Pib kgen"""
    master = field(mandatory=True, type=MasterConfig)
    nodes = field(mandatory=True, type=NodesConfig)


class System(PClass):
    """A System loaded from an Envfile.yaml."""
    cluster = field(mandatory=True, type=Cluster)


def semantic_validate(instance):
    """Additional validation for a decoded Kubefile.yaml.

    TODO: implement
    """
    pass


def load_kubefile(instance):
    """Create System object from decoded Envfile.yaml.

    :return System: parsed envfile.
    :raises ValidationError: if the Envfile.yaml is invalid in some way.
    """
    validate(KUBEFILE_SCHEMA, instance)
    semantic_validate(instance)

    # At the moment the object model is mostly 1-to-1 with the configuration
    # format. In the future that might change; the idea is for the object model
    # to be an abstraction rather than exactly the same as config format, so
    # e.g. same object model might support two different versions of the config
    # format.

    # We do however make some minor changes.
    instance = freeze(instance)

    # 0. Drop unneeded fields:
    instance = instance.remove("Kubefile-version")
    instance = instance.transform(["local", "templates", match_any, "type"], discard)

    return System.create(instance)
