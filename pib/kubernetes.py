"""Kubernetes integration for Pib."""

from pyrsistent import PClass, field, pset_field, pset


class AddressConfigMap(PClass):
    """Kubernetes ConfigMap representation pointing at an InternalService.

    This will be used to give a envfile service the addresses of envfile
    deployments.
    """
    # TODO: When we support external services (e.g. AWS RDS) this may point at
    # those as well.
    # type=InternalService blows up pyrsistent :(
    backend_service = field(mandatory=True)

    def render(self):
        """Convert to a Kubernetes YAML/JSON config (as Python objects)."""
        return {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {
                "name": self.backend_service.deployment.name,
            },
            "data": {
                "host": self.backend_service.deployment.name,
                "port": self.backend_service.deployment.port
            }
        }


class Deployment(PClass):
    """Kubernetes Deployment represenation."""
    name = field(mandatory=True, type=str)
    docker_image = field(mandatory=True, type=str)
    port = field(mandatory=True, type=int)
    address_configmaps = pset_field(AddressConfigMap)

    def render(self):
        result = {
            'spec': {
                'replicas': 1,
                'template': {
                    'spec': {
                        'containers': [{
                            'name': self.name,
                            'imagePullPolicy': 'IfNotPresent',
                            'ports': [{
                                'containerPort': {
                                    'port': self.port
                                }
                            }],
                            'image': self.docker_image
                        }]
                    },
                    'metadata': {
                        'labels': {
                            'name': self.name
                        }
                    }
                }
            },
            'kind': 'Deployment',
            'metadata': {
                'labels': {
                    'name': self.name
                },
                'name': self.name
            },
            'apiVersion': 'extensions/v1beta1'
        }
        env = []
        for configmap in self.address_configmaps:
            for value in ["host", "port"]:
                name = configmap.backend_service.deployment.name
                env.append({
                    "name": "{}_{}".format(name.upper().replace("-", "_"),
                                           value.upper()),
                    "valueFrom": {
                        "configMapKeyRef": {
                            "name": name,
                            "key": value
                        }
                    }
                })
        result["spec"]["template"]["spec"]["containers"][0]["env"] = env
        return result


class InternalService(PClass):
    """Kubernetes Service represenation.

    This can represent either an envfile service or an envfile component.
    """
    deployment = field(mandatory=True, type=Deployment)

    def render(self):
        rendered_deployment = self.deployment.render()
        return {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": rendered_deployment["metadata"],
            "spec": {
                # TODO: only for local minikube, elsewhere want ClusterIP:
                "type": "NodePort",
                "ports": [{
                    "port": self.deployment.port,
                    "targetPort": self.deployment.port,
                    "protocol": "TCP"
                }],
                "selector": rendered_deployment["metadata"]["labels"],
            }
        }


class Ingress(PClass):
    """Kubernetes Ingress representation."""
    exposed_path = field(mandatory=True, type=str)
    backend_service = field(mandatory=True, type=InternalService)

    def render(self):
        name = self.backend_service.deployment.name
        return {
            "apiVersion": "extensions/v1beta1",
            "kind": "Ingress",
            "metadata": {
                "name": name,
            },
            "spec": {
                "rules": [{
                    "http": {
                        "paths": [{
                            "path": self.exposed_path,
                            "backend": {
                                "serviceName": name,
                                "servicePort":
                                self.backend_service.deployment.port,
                            }
                        }]
                    }
                }]
            }
        }


def envfile_to_k8s(envfile):
    """Convert a loaded Envfile.yaml into Kubernetes objects.

    :param envfile System: Envfile to convert.
    :return: `PSet` of K8s objects.
    """
    result = set()
    shared_addressconfigmaps = set()

    def require_to_k8s(requirement, prefix):
        component = envfile.local.templates[requirement.template]
        deployment = Deployment(
            name=prefix + requirement.name + "-component",
            docker_image=component.image,
            port=component.port)
        k8s_service = InternalService(deployment=deployment)
        addrconfigmap = AddressConfigMap(backend_service=k8s_service)
        return deployment, k8s_service, addrconfigmap

    # Shared components are shared, so no prefix:
    for shared_require in envfile.application.requires.values():
        new_objs = require_to_k8s(shared_require, prefix="")
        result |= set(new_objs)
        shared_addressconfigmaps.add(new_objs[-1])

    k8s_services = {}
    for service in envfile.application.services.values():
        # Private components should be namespaced based on the service they're
        # part of, so they get prefix with service name:
        component_prefix = "{}-".format(service.name)
        private_addressconfigmaps = set()
        for private_require in service.requires.values():
            new_objs = require_to_k8s(private_require, prefix=component_prefix)
            result |= set(new_objs)
            private_addressconfigmaps.add(new_objs[-1])

        deployment = Deployment(
            name=service.name,
            docker_image=service.image.image_name,
            port=service.port,
            address_configmaps=shared_addressconfigmaps |
            private_addressconfigmaps)
        k8s_service = InternalService(deployment=deployment)
        k8s_services[service.name] = k8s_service
        ingress = Ingress(
            exposed_path=service.expose.path, backend_service=k8s_service)
        result |= {deployment, k8s_service, ingress}

    return pset(result)
