"""Code for parsing the Envfile."""

from pyrsistent import (PClass, field, pmap_field, freeze, ny as match_any,
                        discard)

from .schema import validate, ENVFILE_SCHEMA, ValidationError


class DockerComponent(PClass):
    """A Docker Component.

    :attr image: The Docker image to run.
    :attr port: The port it listens on.
    """
    name = field(type=str)
    image = field(mandatory=True, type=str)
    port = field(mandatory=True, type=int)


class LocalDeployment(PClass):
    """Runs services and components on Minikube."""
    templates = pmap_field(str, DockerComponent)


class RequiredComponent(PClass):
    """A required component."""
    name = field(mandatory=True, type=str)
    template = field(mandatory=True, type=str)


class DockerImage(PClass):
    """A Docker image."""
    repository = field(mandatory=True, type=str)
    tag = field(mandatory=True, type=str)

    @property
    def image_name(self):
        """Return <repository>:<tag>."""
        return "{}:{}".format(self.repository, self.tag)


class Expose(PClass):
    """How a service should be exposed."""
    # TODO: better structure
    path = field(mandatory=True, type=str)


class Service(PClass):
    """A service."""
    name = field(mandatory=True, type=str)
    image = field(mandatory=True, type=DockerImage)
    port = field(type=(type(None), int), initial=None)
    expose = field(mandatory=True, type=Expose)
    requires = pmap_field(str, RequiredComponent)


class Application(PClass):
    """An application composed of services and components."""
    services = pmap_field(str, Service)
    requires = pmap_field(str, RequiredComponent)


class System(PClass):
    """A System loaded from an Envfile.yaml."""
    local = field(
        mandatory=True, type=LocalDeployment, initial=LocalDeployment())
    remote = pmap_field(str, str)  # TODO: define structure
    application = field(mandatory=True, type=Application)


def semantic_validate(instance):
    """Additional validation for a decoded Envfile.yaml.

    * Validate uniqueness of names: shared requirements and services can't have
      the same name.
    * Validate that each referenced template in a requirement has a matching
      entry in /local/templates/

    """
    unknown_templates = {}
    for name, requires in instance["application"]["requires"].items():
        if name in instance["application"]["services"]:
            raise ValidationError(errors=[
                "/application/requires/{}: the name {} conflicts with service"
                " /application/services/{}".format(name,
                                                   repr(name),
                                                   name),
            ])
        if requires["template"] not in instance["local"]["templates"]:
            unknown_templates["/application/requires/{}/template".format(
                name)] = requires["template"]
    for service_name, service in instance["application"]["services"].items():
        for name, requires in service["requires"].items():
            if name in instance["application"]["requires"]:
                raise ValidationError(errors=[
                    "/application/services/{}/requires/{}: the name {}"
                    " conflicts with /application/requires/{}".format(
                        service_name, name, repr(name), name)
                ])
            if requires["template"] not in instance["local"]["templates"]:
                unknown_templates[
                    "/application/services/{}/requires/{}/template".
                    format(service_name, name)] = requires["template"]
    if unknown_templates:
        raise ValidationError(errors=[
            "{}: the template {} does not exist "
            "in /local/templates".format(path, repr(name))
            for (path, name) in unknown_templates.items()
        ])


def load_envfile(instance):
    """Create System object from decoded Envfile.yaml.

    :return System: parsed envfile.
    :raises ValidationError: if the Envfile.yaml is invalid in some way.
    """
    validate(ENVFILE_SCHEMA, instance)
    semantic_validate(instance)

    # At the moment the object model is mostly 1-to-1 with the configuration
    # format. In the future that might change; the idea is for the object model
    # to be an abstraction rather than exactly the same as config format, so
    # e.g. same object model might support two different versions of the config
    # format.

    # We do however make some minor changes.
    instance = freeze(instance)

    # 0. Drop unneeded fields:
    instance = instance.remove("Envfile-version")
    instance = instance.transform(["local", "templates", match_any, "type"],
                                  discard)

    # 1. Some objects want to know their own name:
    def add_name(mapping):
        # Convert {a: {x: 1}} to {a: {name: a, x: 1}}:
        for key, value in mapping.items():
            mapping = mapping.set(key, value.set("name", key))
        return mapping

    instance = instance.transform(["local", "templates"], add_name)
    instance = instance.transform(["application", "requires"], add_name)
    instance = instance.transform(["application", "services"], add_name)
    instance = instance.transform(
        ["application", "services", match_any, "requires"], add_name)

    # 2. Port is first-class value on DockerComponent:
    def move_port(docker_component):
        port = docker_component["config"]["port"]
        return docker_component.remove("config").set("port", port)

    instance = instance.transform(["local", "templates", match_any], move_port)
    return System.create(instance)
