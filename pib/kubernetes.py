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
    for service in envfile.application.services.values():
        deployment = Deployment(
            name=service.name,
            docker_image=service.image.image_name,
            port=service.port)
        k8s_service = InternalService(deployment=deployment)
        ingress = Ingress(
            exposed_path=service.expose.path, backend_service=k8s_service)
        result |= {deployment, k8s_service, ingress}
    return pset(result)
