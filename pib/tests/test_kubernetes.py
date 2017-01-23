"""Tests for pib.kubernetes."""


def test_render_to_local_kubernetes(envfile):
    """An Envfile renders to a semantically equivalent local k8s config."""
    # 1. Each Envfile service gets a k8s Service and Deployment:

    # 2. If the Envfile service has a `expose` then a k8s Ingress is added:

    # 3. Each Envfile component gets a k8s Service and Deployment:

    # 4. Envfile private components with same name don't have same k8s name:

    # 5. Each Envfile service get a k8s ConfigMap for each private components and shared component:

    # 6. Only one shared component is created even if there are >1 services:
