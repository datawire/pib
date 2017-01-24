"""Tests for pib.kubernetes."""

from pyrsistent import pset

from ..kubernetes import envfile_to_k8s
from .. import kubernetes as k8s
from ..envfile import (System, DockerImage, Application,
                       DockerComponent, RequiredComponent, Expose, Service)

SIMPLE_SYSTEM = System(application=Application(services={
    "myservice": Service(
        name="myservice",
        image=DockerImage(
            repository="examplecom/myservice", tag="1.2"),
        port=1234,
        expose=Expose(path="/abc"))
}))

SIMPLE_K8S_DEPLOYMENT = k8s.Deployment(
    name="myservice", docker_image="examplecom/myservice:1.2", port=1234)


def test_envfile_to_k8s_service():
    """Each Envfile service gets a k8s Service, Deployment and Ingress."""
    expected_deployment = SIMPLE_K8S_DEPLOYMENT
    expected_service = k8s.InternalService(deployment=expected_deployment)
    assert envfile_to_k8s(SIMPLE_SYSTEM) == pset([
        expected_deployment, expected_service, k8s.Ingress(
            exposed_path="/abc", backend_service=expected_service)
    ])


def test_envfile_to_k8s_private_component():
    """
    Each private Envfile component gets a k8s Service, Deployment and
    AddressConfigMap.
    """
    system = SIMPLE_SYSTEM.transform(
        ["application", "services", "myservice", "requires", "mycomponent"],
        RequiredComponent(
            name="mycomponent", template="database"))
    system = SIMPLE_SYSTEM.transform(
        ["local", "components", "mycomponent"],
        DockerComponent(
            name="mycomponent", image="postgres:9.3", port=3535))
    expected_component_deployment = k8s.Deployment(
        name="myservice-mycomponent-component",
        docker_image="postgres:9.3",
        port=3535)
    expected_component_service = k8s.InternalService(
        deployment=expected_component_deployment)
    expected_addrconfigmap = k8s.AddressConfigMap(
        backend_service=expected_component_service)
    expected_deployment = SIMPLE_K8S_DEPLOYMENT.transform(
        ["address_configmaps"], {expected_addrconfigmap})
    expected_service = k8s.InternalService(deployment=expected_deployment)
    assert envfile_to_k8s(system) == pset([
        expected_deployment,
        expected_service,
        k8s.Ingress(
            exposed_path="/abc", backend_service=expected_service),
        expected_component_service,
        expected_component_deployment,
        expected_addrconfigmap,
    ])


def test_envfile_to_k8s_shared_component():
    """
    Each shared Envfile component gets a single k8s Service, Deployment and
    AddressConfigMap.
    """
    system = SIMPLE_SYSTEM.transform(
        ["application", "requires", "mycomponent"],
        RequiredComponent(
            name="mycomponent", template="database"))
    system = system.transform(
        ["local", "components", "database"],
        DockerComponent(
            name="database", image="postgres:9.3", port=3535))
    expected_component_deployment = k8s.Deployment(
        name="mycomponent-component",
        docker_image="postgres:9.3",
        port=3535)
    expected_component_service = k8s.InternalService(
        deployment=expected_component_deployment)
    expected_addrconfigmap = k8s.AddressConfigMap(
        backend_service=expected_component_service)
    expected_deployment = SIMPLE_K8S_DEPLOYMENT.transform(
        ["address_configmaps"], {expected_addrconfigmap})
    expected_service = k8s.InternalService(deployment=expected_deployment)
    assert envfile_to_k8s(system) == pset([
        expected_deployment,
        expected_service,
        k8s.Ingress(
            exposed_path="/abc", backend_service=expected_service),
        expected_component_service,
        expected_component_deployment,
        expected_addrconfigmap,
    ])


# Later, when we do K8s objects -> actual config:
# - Envfile private components for different services but with same name don't
#   have same k8s name.
# - ...
