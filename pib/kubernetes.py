"""Kubernetes integration for Pib."""

from pyrsistent import PClass, field, pmap_field


class Ingress(PClass):
    """Kubernetes Ingress representation."""
    name = field(mandatory=True, type=str)
    exposed_path = field(mandatory=True, type=str)
    backend_service_name = field(mandatory=True, type=str)
    backend_service_port = field(mandatory=True, type=int)


class InternalService(PClass):
    """Kubernetes Service represenation."""
    name = field(mandatory=True, type=str)
    labels = pmap_field(str, str)
    selector = pmap_field(str, str)
    exposed_port = field(mandatory=True, type=int)
    target_port = field(mandatory=True, type=int)
    type = field(mandatory=True, type=str)  # Either ClusterIP or NodePort


class Deployment(PClass):
    """Kubernetes Deployment represenation.

    As a first pass we assume pods have same name and labels as the deployment.
    """
    name = field(mandatory=True, type=str)
    labels = pmap_field(str, str)
    docker_image = field(mandatory=True, type=str)
    port = field(mandatory=True, type=int)
    replicas = field(mandatory=True, type=int)


class ConfigMap(PClass):
    """Kubernetes ConfigMap representation."""
    name = field(mandatory=True, type=str)
    data = pmap_field(str, (int, str))
