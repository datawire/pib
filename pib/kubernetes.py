"""Kubernetes configuration integration for Pib."""

from pyrsistent import PClass, field, pset_field, pset, pmap_field, thaw


class RenderingOptions(PClass):
    """Define how objects should be rendered."""
    # map service name to Docker image tag:
    tag_overrides = pmap_field(str, str)
    # typically "ClusterIP" or "NodePort":
    private_service_type = field(str, initial="ClusterIP")


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


class IRenderToKubernetes(object):
    """This object can be rendered to a Kubernetes configuration object."""

    def render(self, options):
        """Render to k8s config object.

        :param options RenderingOptions: how to render.
        :return: Python dict that can be serialized to JSON/YAML.
        """


class ExternalRequiresConfigMap(PClass, IRenderToKubernetes):
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


class InternalRequiresConfigMap(PClass, IRenderToKubernetes):
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


class Deployment(PClass, IRenderToKubernetes):
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


class InternalService(PClass, IRenderToKubernetes):
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
                "type": options.private_service_type,
                "ports": [{
                    "port": self.deployment.port,
                    "targetPort": self.deployment.port,
                    "protocol": "TCP"
                }],
                "selector": rendered_deployment["metadata"]["labels"],
            }
        }


class Ingress(PClass, IRenderToKubernetes):
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


class IBuildKubernetesConfigs(object):
    """Construct Kubernetes configurations."""

    def get_all(self):
        """Get all Kubernetes configs.

        :return: set of ``IRenderToKubernetes``.
        """

    def configmaps_for_service(self, service_name):
        """
        Return the ConfigMaps for the given service.

        :param service_name str: The name of the service.
        :return: set of ``ExternalRequiresConfigMap`` and
            ``InternalRequiresConfigMap`` objects.
        """


def resource_configmap_k8s_name(service_name, resource_name):
    """
    Get the k8s name for the ConfigMap for a resource.

    :param service_name: The name of the service, or None if this is shared
        resource.
    :param resource_name str: The resource name.
    """
    if service_name is None:
        return resource_name
    # Private resources should be namespaced based on the service
    # they're part of, so they get prefix with service name:
    return "{}---{}".format(service_name, resource_name)


class Minikube(IBuildKubernetesConfigs):
    """Generate k8s configs for local (minikube) deploys."""
    def _require_to_k8s(self, envfile, requirement, service_name):
        resource = envfile.local.templates[requirement.template]
        deployment = Deployment(
            name=resource_configmap_k8s_name(service_name, requirement.name),
            docker_image=resource.image,
            port=resource.config["port"])
        k8s_service = InternalService(deployment=deployment)
        addrconfigmap = InternalRequiresConfigMap(
            backend_service=k8s_service,
            resource_name=requirement.name,
            data=resource.config.remove("port"))
        return deployment, k8s_service, addrconfigmap

    def __init__(self, envfile):
        self._all = set()
        self._shared_addressconfigmaps = set()
        self._private_addressconfigmaps = {}

        # Shared resources are shared, so no prefix:
        for shared_require in envfile.application.requires.values():
            new_objs = self._require_to_k8s(envfile, shared_require, None)
            self._all |= set(new_objs)
            self._shared_addressconfigmaps.add(new_objs[-1])

        for service in envfile.application.services.values():
            self._private_addressconfigmaps[service.name] = set()
            for private_require in service.requires.values():
                new_objs = self._require_to_k8s(envfile, private_require,
                                                service.name)
                self._all |= set(new_objs)
                self._private_addressconfigmaps[service.name].add(new_objs[-1])

    def get_all(self):
        return self._all

    def configmaps_for_service(self, service_name):
        return (self._shared_addressconfigmaps |
                self._private_addressconfigmaps[service_name])


def envfile_to_k8s(envfile, build_configs):
    """Convert a loaded Envfile.yaml into Kubernetes objects.

    :param envfile System: Envfile to convert.
    :param build_configs IBuildKubernetesConfigs: Additional configs.

    :return: `PSet` of K8s objects.
    """
    result = set()

    for service in envfile.application.services.values():
        deployment = Deployment(
            name=service.name,
            docker_image=service.image.image_name,
            port=service.port,
            address_configmaps=build_configs.configmaps_for_service(
                service.name))
        k8s_service = InternalService(deployment=deployment)
        ingress = Ingress(
            exposed_path=service.expose.path, backend_service=k8s_service)
        result |= {deployment, k8s_service, ingress}

    return pset(result | build_configs.get_all())
