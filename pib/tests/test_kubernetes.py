"""Tests for pib.kubernetes.

TODO: assumes local-only!
"""

from pyrsistent import pset

from ..kubernetes import envfile_to_k8s
from .. import kubernetes as k8s
from ..envfile import (System, DockerImage, Application, DockerComponent,
                       RequiredComponent, Expose, Service, LocalDeployment)

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
    system = system.transform(
        ["local", "templates", "database"],
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
        ["local", "templates", "database"],
        DockerComponent(
            name="database", image="postgres:9.3", port=3535))
    expected_component_deployment = k8s.Deployment(
        name="mycomponent-component", docker_image="postgres:9.3", port=3535)
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


def test_envfile_k8s_shared_component_once():
    """
    Envfile shared components only appear once even if there are multiple
    services.
    """
    system = System(
        application=Application(
            services={
                "myservice": Service(
                    name="myservice",
                    image=DockerImage(
                        repository="examplecom/myservice", tag="1.2"),
                    port=1234,
                    expose=Expose(path="/abc")),
                "myservice2": Service(
                    name="myservice2",
                    image=DockerImage(
                        repository="examplecom/myservice", tag="1.2"),
                    port=1234,
                    expose=Expose(path="/abcd"))
            },
            requires={
                "mycomponent": RequiredComponent(
                    name="mycomponent", template="database")
            }, ),
        local=LocalDeployment(templates={
            "database": DockerComponent(
                name="database", image="postgres:9.3", port=3535)
        }))
    k8s_objects = envfile_to_k8s(system)
    assert len([
        o for o in k8s_objects
        if isinstance(o, k8s.Deployment) and "mycomponent" in o.name
    ]) == 1


def test_envfile_k8s_private_component_is_private():
    """
    Envfile private components for different services but with same name don't
    have same k8s name.
    """
    system = System(
        application=Application(services={
            "myservice": Service(
                name="myservice",
                image=DockerImage(
                    repository="examplecom/myservice", tag="1.2"),
                port=1234,
                expose=Expose(path="/abc"),
                requires={
                    "mycomponent": RequiredComponent(
                        name="mycomponent", template="database")
                }),
            "myservice2": Service(
                name="myservice2",
                image=DockerImage(
                    repository="examplecom/myservice", tag="1.2"),
                port=1234,
                expose=Expose(path="/abcd"),
                requires={
                    "mycomponent": RequiredComponent(
                        name="mycomponent", template="database")
                })
        }),
        local=LocalDeployment(templates={
            "database": DockerComponent(
                name="database", image="postgres:9.3", port=3535)
        }))
    k8s_objects = envfile_to_k8s(system)
    assert {
        o.name
        for o in k8s_objects
        if isinstance(o, k8s.Deployment) and "mycomponent" in o.name
    } == {
        "myservice-mycomponent-component", "myservice2-mycomponent-component"
    }


def test_render_addressconfigmap():
    """An AddressConfigMap renders to a k8s ConfigMap."""
    addrconfigmap = k8s.AddressConfigMap(backend_service=k8s.InternalService(
        deployment=SIMPLE_K8S_DEPLOYMENT))
    assert addrconfigmap.render() == {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {
            "name": "myservice",
        },
        "data": {
            "host": "myservice",
            "port": 1234,
        }
    }


def test_render_deployment():
    """A Deployment renders to a k8s Deployment."""
    assert SIMPLE_K8S_DEPLOYMENT.render() == {
        'spec': {
            'replicas': 1,
            'template': {
                'spec': {
                    'containers': [{
                        'name': "myservice",
                        'imagePullPolicy': 'IfNotPresent',
                        'ports': [{
                            'containerPort': {
                                'port': 1234,
                            }
                        }],
                        'image': "examplecom/myservice:1.2",
                    }]
                },
                'metadata': {
                    'labels': {
                        'name': "myservice",
                    }
                }
            }
        },
        'kind': 'Deployment',
        'metadata': {
            'labels': {
                'name': "myservice",
            },
            'name': "myservice",
        },
        'apiVersion': 'extensions/v1beta1'
    }


def test_render_internalservice():
    """An InternalService renders to a k8s Service."""
    deployment_rendered = SIMPLE_K8S_DEPLOYMENT.render()
    rendered = k8s.InternalService(deployment=SIMPLE_K8S_DEPLOYMENT).render()
    assert len(rendered) == 4
    assert rendered["apiVersion"] == "v1"
    assert rendered["kind"] == "Service"
    assert rendered["metadata"] == deployment_rendered["metadata"]
    expected_spec = {
        "type": "NodePort",  # TODO: only for local minikube setup!
        "ports": [{
            "port": 1234,
            "targetPort": 1234,
            "protocol": "TCP"
        }]
    }
    expected_spec["selector"] = deployment_rendered["metadata"]["labels"]
    assert rendered["spec"] == expected_spec


def test_render_ingress():
    """An Ingress renders to a k8s Ingress."""
    ingress = k8s.Ingress(
        exposed_path="/abc",
        backend_service=k8s.InternalService(deployment=SIMPLE_K8S_DEPLOYMENT))
    assert ingress.render() == {
        "apiVersion": "extensions/v1beta1",
        "kind": "Ingress",
        "metadata": {
            "name": "myservice"
        },
        "spec": {
            "rules": [{
                "http": {
                    "paths": [{
                        "path": "/abc",
                        "backend": {
                            "serviceName": "myservice",
                            "servicePort": 1234
                        }
                    }]
                }
            }]
        }
    }
