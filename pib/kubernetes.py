"""Kubernetes integration for Pib."""

from pyrsistent import PClass, field, pset_field


class AddressConfigMap(PClass):
    """Kubernetes ConfigMap representation pointing at an InternalService.

    This will be used to give a envfile service the addresses of envfile
    deployments.
    """
    # TODO: When we support external services (e.g. AWS RDS) this may point at
    # those as well:
    backend_service = field(
        mandatory=True, type="pib.kubernetes.InternalService")


class Deployment(PClass):
    """Kubernetes Deployment represenation."""
    name = field(mandatory=True, type=str)
    docker_image = field(mandatory=True, type=str)
    port = field(mandatory=True, type=int)
    replicas = field(mandatory=True, type=int)
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
