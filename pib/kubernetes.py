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


class Deployment(PClass):
    """Kubernetes Deployment represenation."""
    name = field(mandatory=True, type=str)
    docker_image = field(mandatory=True, type=str)
    port = field(mandatory=True, type=int)
    address_configmaps = pset_field(AddressConfigMap)


class InternalService(PClass):
    """Kubernetes Service represenation.

    This can represent either an envfile service or an envfile component.
    """
    deployment = field(mandatory=True, type=Deployment)


class Ingress(PClass):
    """Kubernetes Ingress representation."""
    exposed_path = field(mandatory=True, type=str)
    backend_service = field(mandatory=True, type=InternalService)


def envfile_to_k8s(envfile):
    """Convert a loaded Envfile.yaml into Kubernetes objects.

    :param envfile System: Envfile to convert.
    :return: `PSet` of K8s objects.
    """
    result = set()
    shared_addressconfigmaps = set()

    def require_to_k8s(requirement, prefix):
        component = envfile.local.components[requirement.template]
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
            address_configmaps=shared_addressconfigmaps | private_addressconfigmaps)
        k8s_service = InternalService(deployment=deployment)
        k8s_services[service.name] = k8s_service
        ingress = Ingress(
            exposed_path=service.expose.path, backend_service=k8s_service)
        result |= {deployment, k8s_service, ingress}

    return pset(result)
