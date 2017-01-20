"""Code for parsing the Envfile."""

# from yaml import safe_load
from pyrsistent import PClass, field, pvector_field, pmap_field

# from .schema import validate

# Until we have a schema and can use, use an python-jsonschema-objects, just
# use a thing that turns dictionaries into objects with attributes:


class DockerComponent(PClass):
    """A Docker Component.

    :attr image: The Docker image to run.
    :attr port: The port it listens on.
    """
    image = field(type=str)
    port = field(type=int)


class MinikubeEnvironment(PClass):
    """Runs services and components on Minikube."""
    components = pvector_field(DockerComponent)


class RequiredComponent(PClass):
    """A required component."""
    name = field(type=str)
    template = field(type=str)


class Service(PClass):
    """A service."""
    name = field(type=str)
    # image = ...


class Application(PClass):
    """An application composed of services and components."""
    services = pmap_field(str, Service)
    required_components = pmap_field(str, RequiredComponent)


class System(PClass):
    """A System loaded from an Envfile.yaml."""
    environments = pvector_field(MinikubeEnvironment)


def load_env_file(path_to_repo):
    """Load Envfile from path, return AttrDict."""
    # with (path_to_repo / "Envfile.yaml").open() as f:
    #    return AttrDict(safe_load(f.read()))
    pass
