"""Kubernetes configuration integration for Pib."""

from pyrsistent import PClass, field, pset_field, pset, pmap_field, thaw


class RenderingOptions(PClass):
    """Define how objects should be rendered."""
    tag_overrides = pmap_field(str, str)  # map service name to Docker image tag
    # TODO: eventually ClusterIP vs NodePort can go here


def _render_configmap(name, data):
    """
    Return JSON for a ConfigMap.

    :param name str: The name of the configmap.
    :param data dict: The data included in the ConfigMap.
    """
    return {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {
            "name": name,
        },
        "data": data
    }


class ExternalRequiresConfigMap(PClass):
    """
    Kubernetes ConfigMap pointing an external resource (e.g. AWS RDS) for a
    specific required resource.
    """
    # TODO the name should be either the requires name for shared requires, or
    # "<service name>---<requires name>" for private resources:
    name = field(mandatory=True, type=str)  # The name of this ConfigMap
    resource_name = field(mandatory=True, type=str)  # original resource name
    data = pmap_field(str, str)  # the information stored in the ConfigMap

    def get_full_data(self):
        """:return PMap: the full set of values in the configmap."""
        return self.data

    def render(self, options):
        return _render_configmap(self.name, thaw(self.data))


class InternalRequiresConfigMap(PClass):
    """
    Kubernetes ConfigMap representation pointing at an InternalService used for
    a resource.

    This will be used to give a envfile service the addresses of envfile
    resources when used in local (minikube) mode.
    """
    # type=InternalService blows up pyrsistent :(
    backend_service = field(mandatory=True)
    resource_name = field(mandatory=True, type=str)  # original resource name
    data = pmap_field(str, str)  # the information stored in the ConfigMap

    def get_full_data(self):
        """:return PMap: the full set of values in the configmap."""
        return self.data.update({
            "host": self.backend_service.deployment.name,
            "port": str(self.backend_service.deployment.port),
        })

    def render(self, options):
        return _render_configmap(self.backend_service.deployment.name,
                                 thaw(self.get_full_data()))


class Deployment(PClass):
    """Kubernetes Deployment represenation."""
    name = field(mandatory=True, type=str)
    docker_image = field(mandatory=True, type=str)
    port = field(mandatory=True, type=int)
    address_configmaps = pset_field((InternalRequiresConfigMap,
                                     ExternalRequiresConfigMap))

    def render(self, options):
        docker_image = self.docker_image
        tag = options.tag_overrides.get(self.name)
        if tag is not None:
            image_parts = self.docker_image.split(":")
            image_parts[-1] = tag
            docker_image = ":".join(image_parts)
        result = {
            'spec': {
                'replicas': 1,
                'template': {
                    'spec': {
                        'containers': [{
                            'name': self.name,
                            'imagePullPolicy': 'IfNotPresent',
                            'ports': [{
                                'containerPort': self.port,
                            }],
                            'image': docker_image,
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
            for key in sorted(configmap.get_full_data()):
                # Notice that the environment variables are based on the
                # original name of the resource, not the namespaced Kubernetes
                # variant; from the service's point of view the original name
                # is what counts.
                name = configmap.resource_name
                env.append({
                    "name":
                    "{}_RESOURCE_{}".format(name.upper().replace("-", "_"),
                                            key.upper()),
                    "valueFrom": {
                        "configMapKeyRef": {
                            # ConfigMap k8s object has same name as the
                            # Deployment it points at:
                            "name": configmap.backend_service.deployment.name,
                            "key": key
                        }
                    }
                })
        result["spec"]["template"]["spec"]["containers"][0]["env"] = env
        return result


class InternalService(PClass):
    """Kubernetes Service represenation.

    This can represent either an envfile service or an envfile resource.
    """
    deployment = field(mandatory=True, type=Deployment)

    def render(self, options):
        rendered_deployment = self.deployment.render(options)
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

    def render(self, options):
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
        resource = envfile.local.templates[requirement.template]
        deployment = Deployment(
            name=prefix + requirement.name,
            docker_image=resource.image,
            port=resource.config["port"])
        k8s_service = InternalService(deployment=deployment)
        addrconfigmap = InternalRequiresConfigMap(
            backend_service=k8s_service,
            resource_name=requirement.name,
            data=resource.config.remove("port"))
        return deployment, k8s_service, addrconfigmap

    # Shared resources are shared, so no prefix:
    for shared_require in envfile.application.requires.values():
        new_objs = require_to_k8s(shared_require, prefix="")
        result |= set(new_objs)
        shared_addressconfigmaps.add(new_objs[-1])

    k8s_services = {}
    for service in envfile.application.services.values():
        # Private resources should be namespaced based on the service they're
        # part of, so they get prefix with service name:
        resource_prefix = "{}---".format(service.name)
        private_addressconfigmaps = set()
        for private_require in service.requires.values():
            new_objs = require_to_k8s(private_require, prefix=resource_prefix)
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
