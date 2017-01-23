"""Code for parsing the Envfile."""

from yaml import safe_load
from pyrsistent import PClass, field, pvector_field, pmap_field

from .schema import validate, ENVFILE_SCHEMA


class DockerComponent(PClass):
    """A Docker Component.

    :attr image: The Docker image to run.
    :attr port: The port it listens on.
    """
    image = field(type=str)
    port = field(type=int)


class LocalDeployment(PClass):
    """Runs services and components on Minikube."""
    components = pvector_field(DockerComponent)


class RequiredComponent(PClass):
    """A required component."""
    name = field(type=str)
    template = field(type=str)


class DockerImage(PClass):
    """A Docker image."""
    repository = field(type=str)
    tag = field(type=str)


class Expose(PClass):
    """How a service should be exposed."""
    # TODO: better structure
    path = field(type=str)


class Service(PClass):
    """A service."""
    name = field(type=str)
    image = field(type=DockerImage)
    port = field(type=int, optional=True)
    expose = field(type=Expose)
    requires = pmap_field(str, RequiredComponent)


class Application(PClass):
    """An application composed of services and components."""
    services = pmap_field(str, Service)
    requires = pmap_field(str, RequiredComponent)


class System(PClass):
    """A System loaded from an Envfile.yaml."""
    local = field(type=LocalDeployment)
    remote = pmap_field(str, str)  # TODO: define structure
    application = field(type=Application)


def load_env_file(path_to_repo):
    """Load Envfile from path, return AttrDict."""
    with (path_to_repo / "Envfile.yaml").open() as f:
        data = safe_load(f.read())
    validate(ENVFILE_SCHEMA, data)
    # At the moment the object model is pretty much 1-to-1 with the
    # configuration format. In the future that might change; the idea is for
    # the object model to be an abstraction rather than exactly the same as
    # config format, so e.g. same object model might support two different
    # versions of the config format.
    return System.create(safe_load(f.read()))
