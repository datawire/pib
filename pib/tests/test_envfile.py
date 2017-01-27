"""Tests for pib.envfile."""

import pytest
from yaml import safe_load

from ..schema import ValidationError
from ..envfile import (load_envfile, System, LocalDeployment, DockerImage,
                       Application, DockerResource, RequiredResource, Expose,
                       Service)


def test_load_invalid_instance():
    """
    Loading invalid instance of the Envfile.yaml schema raises an exception.
    """
    with pytest.raises(ValidationError):
        load_envfile({"not": "valid"})


def test_service_shared_resource_name_uniqueness():
    """Shared requires and services cannot have the same name."""
    bad_instance = """\
Envfile-version: 1

local:
  templates:
    "postgresql-v96":
      type: docker
      image: postgres:9.6
      config:
        port: 5432

application:
  requires:
    shared:
      template: postgresql-v96
  services:
    shared:
      image:
        repository: datawire/hello
        tag: "1.0"
      port: 5100
      expose:
        path: /hello
      requires: {}
"""
    with pytest.raises(ValidationError) as result:
        load_envfile(safe_load(bad_instance))
    assert result.value.errors == [
        "/application/requires/shared: the name 'shared' conflicts "
        "with service /application/services/shared"
    ]


def test_service_private_resource_name_uniqueness():
    """Private requires cannot have the same name as a shared requires."""
    bad_instance = """\
Envfile-version: 1

local:
  templates:
    "postgresql-v96":
      type: docker
      image: postgres:9.6
      config:
        port: 5432

application:
  requires:
    shared:
      template: postgresql-v96
  services:
    myservice:
      image:
        repository: datawire/hello
        tag: "1.0"
      port: 5100
      expose:
        path: /hello
      requires:
        shared:
          template: postgresql-v96
"""
    with pytest.raises(ValidationError) as result:
        load_envfile(safe_load(bad_instance))
    assert result.value.errors == [
        "/application/services/myservice/requires/shared: the name 'shared'"
        " conflicts with /application/requires/shared"
    ]


def test_unknown_template_name():
    """References to unknown templates result in validation error."""
    bad_instance = """\
Envfile-version: 1

local:
  templates: {}

application:
  requires:
    shared:
      template: template1
  services:
    myservice:
      image:
        repository: datawire/hello
        tag: "1.0"
      port: 5100
      expose:
        path: /hello
      requires:
        private:
          template: template2
"""
    with pytest.raises(ValidationError) as result:
        load_envfile(safe_load(bad_instance))
    assert sorted(result.value.errors) == sorted([
        "/application/requires/shared/template: "
        "the template 'template1' does not exist in /local/templates",
        "/application/services/myservice/requires/private/template: "
        "the template 'template2' does not exist in /local/templates",
    ])


INSTANCE = """\
Envfile-version: 1

local:
  templates:
    "redis-v3":
      type: docker
      image: redis/redis:3
      config:
        port: 6379

    "postgresql-v96":
      type: docker
      image: postgres:9.6
      config:
        port: 5432

remote:
  type: kubernetes

application:
  requires:
    shared-db:
      template: postgresql-v96
  services:
    cloud-service-pipeline-example:
      image:
        repository: datawire/hello
        tag: "1.0"
      port: 5100
      expose:
        path: /hello
      requires:
        hello-db:
          template: postgresql-v96
"""


def test_load_valid_instance():
    """
    Loading a valid instance of Envfile.yaml parses it into matching tree of
    objects from the envfile module.
    """
    instance = safe_load(INSTANCE)
    assert load_envfile(instance) == System(
        application=Application(
            requires={
                "shared-db": RequiredResource(
                    name="shared-db", template="postgresql-v96")
            },
            services={
                "cloud-service-pipeline-example": Service(
                    name="cloud-service-pipeline-example",
                    image=DockerImage(
                        repository="datawire/hello", tag="1.0"),
                    port=5100,
                    expose=Expose(path="/hello"),
                    requires={
                        "hello-db": RequiredResource(
                            name="hello-db", template="postgresql-v96")
                    })
            }),
        remote={"type": "kubernetes"},
        local=LocalDeployment(templates={
            "redis-v3": DockerResource(
                name="redis-v3", image="redis/redis:3", port=6379),
            "postgresql-v96": DockerResource(
                name="postgresql-v96", image="postgres:9.6", port=5432)
        }))
