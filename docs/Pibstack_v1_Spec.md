# Pibstack file

The Pibstack file describes requirements for deploying a service. The Pibstack is the source of truth for the "form" of a service which means it indicates requirements such as needed components (e.g. Redis) and essential information such as what Docker repository to retrieve an image from.

## Specification

### Serialization

A Pibstack file is stored and transmitted as a single YAML document that **MUST BE** JSON serializable. In practice this means YAML-specific features such as multiple documents per file is not allowed.

### Naming

A Pibstack file may be named as either `pibstack[.yaml]`, `Pibstack[.yaml]`. The `.yaml` extension is optional.

### Structure

A Pibstack is composed of a root YAML dictionary that contains nested dictionaries and lists.

1. The root dictionary must have a field `pibstackVersion:` `(type: Int)` which indicates the version of the specification used.

2. The root **MUST** have a field [`image` `(type = ImageSpec)`](#ImageSpec) which indicates the essential information about the Docker image used.

3. The root **MAY** have a field [`requires` `(type = RequiresSpec)`](#RequiresSpec)  which indicates what services / components need to be run for this service to start and operate.

4. The root **MAY** have a field [`expose` `(type = ExposeSpec)`](#ExposeSpec)  which indicates how the service should be publicly exposed (e.g. via HTTP).

1. The root dictionary must have a field `name` `(type: String)` which indicates the name of the service.

For example:

```yaml
pibstackVersion: 1

image:
  repository: "datawire/billing-api"

requires:
  - type: "component"
    template: "redis-v3"
```

### ImageSpec

The ImageSpec is used to configure how a Docker image is resolved for deployment.

1. A ImageSpec **MUST** have a field `repository` `(type = String)` which indicates the Docker repository for the service.
2. A ImageSpec **MUST** have a field `port` `(type = Int)` which indicates the port number the service listens on (i.e. is exposed by the container).

### RequiresSpec

The RequiresSpec object indicates a service has specific dependencies that **MUST** be satisfied before it can be deployed. The RequireSpec is written as a list of dependencies that must be satisfied.

#### RequiresSpecEntry

Each entry in the RequiresSpec should have the following format:

1. The entry **MUST** have a `type` `(type = String)` field that indicates how the system should attempt to satisfy the requirement.
2. The entry **MUST** have a `template` `(type = String)` field that indicates the template to use when creating the requirement.
   This aids the deployment system in satisfying the requirement.


### InfoSpec

The InfoSpec object provides general information about a service, for example, name, description, maintainers and project website. An InfoSpec is entirely optional.


### ExposeSpec

The ExposeSpec object indicates how a service should be exposed to the outside world.
Currently only a path on a HTTP ingress service is supported, using a `path` key:

```yaml
expose:
  path: /myapp
```
