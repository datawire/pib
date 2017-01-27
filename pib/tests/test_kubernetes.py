"""Tests for pib.kubernetes.

TODO: assumes local-only!
"""

from pyrsistent import pset

from ..kubernetes import envfile_to_k8s
from .. import kubernetes as k8s
from ..envfile import (System, DockerImage, Application, DockerResource,
                       RequiredResource, Expose, Service, LocalDeployment)

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


def test_envfile_to_k8s_private_resource():
    """
    Each private Envfile resource gets a k8s Service, Deployment and
    InternalRequiresConfigMap.
    """
    system = SIMPLE_SYSTEM.transform(
        ["application", "services", "myservice", "requires", "myresource"],
        RequiredResource(
            name="myresource", template="database"))
    system = system.transform(
        ["local", "templates", "database"],
        DockerResource(
            name="myresource", image="postgres:9.3", config=dict(port=3535,
                                                                 another="value")))
    expected_resource_deployment = k8s.Deployment(
        name="myservice---myresource",
        docker_image="postgres:9.3",
        port=3535)
    expected_resource_service = k8s.InternalService(
        deployment=expected_resource_deployment)
    expected_addrconfigmap = k8s.InternalRequiresConfigMap(
        backend_service=expected_resource_service,
        resource_name="myresource",
        data={"another": "value"})
    expected_deployment = SIMPLE_K8S_DEPLOYMENT.transform(
        ["address_configmaps"], {expected_addrconfigmap})
    expected_service = k8s.InternalService(deployment=expected_deployment)
    assert envfile_to_k8s(system) == pset([
        expected_deployment,
        expected_service,
        k8s.Ingress(
            exposed_path="/abc", backend_service=expected_service),
        expected_resource_service,
        expected_resource_deployment,
        expected_addrconfigmap,
    ])


def test_envfile_to_k8s_shared_resource():
    """
    Each shared Envfile resource gets a single k8s Service, Deployment and
    InternalRequiresConfigMap.
    """
    system = SIMPLE_SYSTEM.transform(
        ["application", "requires", "myresource"],
        RequiredResource(
            name="myresource", template="database"))
    system = system.transform(
        ["local", "templates", "database"],
        DockerResource(
            name="database", image="postgres:9.3", config=dict(port=3535)))
    expected_resource_deployment = k8s.Deployment(
        name="myresource", docker_image="postgres:9.3", port=3535)
    expected_resource_service = k8s.InternalService(
        deployment=expected_resource_deployment)
    expected_addrconfigmap = k8s.InternalRequiresConfigMap(
        backend_service=expected_resource_service,
        resource_name="myresource")
    expected_deployment = SIMPLE_K8S_DEPLOYMENT.transform(
        ["address_configmaps"], {expected_addrconfigmap})
    expected_service = k8s.InternalService(deployment=expected_deployment)
    assert envfile_to_k8s(system) == pset([
        expected_deployment,
        expected_service,
        k8s.Ingress(
            exposed_path="/abc", backend_service=expected_service),
        expected_resource_service,
        expected_resource_deployment,
        expected_addrconfigmap,
    ])


def test_envfile_k8s_shared_resource_once():
    """
    Envfile shared resources only appear once even if there are multiple
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
                "myresource": RequiredResource(
                    name="myresource", template="database")
            }, ),
        local=LocalDeployment(templates={
            "database": DockerResource(
                name="database", image="postgres:9.3", config=dict(port=3535))
        }))
    k8s_objects = envfile_to_k8s(system)
    assert len([
        o for o in k8s_objects
        if isinstance(o, k8s.Deployment) and "myresource" in o.name
    ]) == 1


def test_envfile_k8s_private_resource_is_private():
    """
    Envfile private resources for different services but with same name don't
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
                    "myresource": RequiredResource(
                        name="myresource", template="database")
                }),
            "myservice2": Service(
                name="myservice2",
                image=DockerImage(
                    repository="examplecom/myservice", tag="1.2"),
                port=1234,
                expose=Expose(path="/abcd"),
                requires={
                    "myresource": RequiredResource(
                        name="myresource", template="database")
                })
        }),
        local=LocalDeployment(templates={
            "database": DockerResource(
                name="database", image="postgres:9.3", config=dict(port=3535))
        }))
    k8s_objects = envfile_to_k8s(system)
    assert {
        o.name
        for o in k8s_objects
        if isinstance(o, k8s.Deployment) and "myresource" in o.name
    } == {
        "myservice---myresource", "myservice2---myresource"
    }


def test_render_externalrequiresconfigmap():
    """A ConfigMap renders to a k8s ConfigMap."""
    addrconfigmap = k8s.ExternalRequiresConfigMap(
        name="myservice---the-resource",
        resource_name="the-resource",
        data={"random": "value", "another": "hello"})
    assert addrconfigmap.render(k8s.RenderingOptions()) == {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {
            "name": "myservice---the-resource",
        },
        "data": {
            "random": "value",
            "another": "hello",
        }
    }


def test_render_internalrequiresconfigmap():
    """An InternalRequiresConfigMap renders to a k8s ConfigMap."""
    addrconfigmap = k8s.InternalRequiresConfigMap(
        backend_service=k8s.InternalService(deployment=SIMPLE_K8S_DEPLOYMENT),
        resource_name="the-resource",
        data={"random": "value"})
    assert addrconfigmap.render(k8s.RenderingOptions()) == {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {
            "name": "myservice",
        },
        "data": {
            "host": "myservice",
            "port": "1234",
            "random": "value",
        }
    }


def test_render_deployment():
    """A Deployment renders to a k8s Deployment."""
    assert SIMPLE_K8S_DEPLOYMENT.render(k8s.RenderingOptions()) == {
        'spec': {
            'replicas': 1,
            'template': {
                'spec': {
                    'containers': [{
                        'name': "myservice",
                        'imagePullPolicy': 'IfNotPresent',
                        'ports': [{
                            'containerPort': 1234,
                        }],
                        'image': "examplecom/myservice:1.2",
                        'env': [],
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


def test_render_deployment_with_configmaps():
    """A Deployment with InternalRequiresConfigMaps turns them into env variables."""
    addrconfigmap = k8s.InternalRequiresConfigMap(
        resource_name="thedb",
        data={"another": "value"},
        backend_service=k8s.InternalService(
            deployment=SIMPLE_K8S_DEPLOYMENT.set(
                "name", "myservice---thedb").set("port", 5678)))
    deployment_with_configmap = SIMPLE_K8S_DEPLOYMENT.set("address_configmaps",
                                                          {addrconfigmap})
    expected = SIMPLE_K8S_DEPLOYMENT.render(k8s.RenderingOptions())
    env = [
        {
            "name": "THEDB_RESOURCE_ANOTHER",
            "valueFrom": {
                "configMapKeyRef": {
                    "name": "myservice---thedb",
                    "key": "another",
                }
            }
        },
        {
            "name": "THEDB_RESOURCE_HOST",
            "valueFrom": {
                "configMapKeyRef": {
                    "name": "myservice---thedb",
                    "key": "host",
                }
            }
        },
        {
            "name": "THEDB_RESOURCE_PORT",
            "valueFrom": {
                "configMapKeyRef": {
                    "name": "myservice---thedb",
                    "key": "port",
                }
            }
        },
    ]
    expected["spec"]["template"]["spec"]["containers"][0]["env"] = env
    assert deployment_with_configmap.render(k8s.RenderingOptions()) == expected


def test_render_deployment_with_tag_overrides():
    """Tag overrides override the tag in the config when rendering a Deployment."""
    options = k8s.RenderingOptions(tag_overrides={"myservice": "customtag"})
    assert SIMPLE_K8S_DEPLOYMENT.render(options)["spec"]["template"]["spec"][
        "containers"][0]["image"] == "examplecom/myservice:customtag"


def test_render_internalservice():
    """An InternalService renders to a k8s Service."""
    deployment_rendered = SIMPLE_K8S_DEPLOYMENT.render(k8s.RenderingOptions())
    rendered = k8s.InternalService(
        deployment=SIMPLE_K8S_DEPLOYMENT).render(k8s.RenderingOptions())
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
    assert ingress.render(k8s.RenderingOptions()) == {
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
