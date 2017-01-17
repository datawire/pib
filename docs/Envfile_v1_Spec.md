# Environments.pib

The `Envfile` (for lack of better name) contains the system definition.

## Specification

### Serialization

An Envfile file is stored and transmitted as a single YAML document that **MUST BE** JSON serializable. In practice this means YAML-specific features such as multiple documents per file is not allowed.

### Naming

An Envfile file may be named as either `envfile[.yaml]`, `Envfile[.yaml]`. The `.yaml` extension is optional.

### Structure

An Envfile is composed of a root YAML dictionary that contains nested dictionaries and lists.

1. The root MAY have a field `__version:` `(type: Int)` which indicates the version of the specification used. If the `__version` field is omitted or null then the latest is always assumed.

2. The root MUST have a field [`clusters` `(type = ClusterSpec`)](#ClusterSpec) which maps a named environment (e.g. `prod`) to a Kubernetes API endpoint.

3. The root MUST have a field [`components` `(type = ComponentSpec`)](#ComponentSpec) which maps named components to different configurations for each named environment.

4. The root MUST have a field [`applications` `(type = ApplicationSpec`)](#ApplicationSpec).

Example:

```yaml
---
# file: Environments.pib

__version: 1

environments:
    local:
        address: localhost
        components:
            "redis-v3":
                type: docker
                image: redis/redis:3
                config: {}
                
            "postgressql-v96":
                type: docker
                image: postgres/postgres:9.6
                config: {}
                
    test:
        address: test.api.k8s.example.org
        components:
            "redis-v3":
                type: aws
                config: {}
            
            "postgressql-v96":
                type: aws
                config: {}
                
    prod:
        address: prod.api.k8s.example.org
        components:
            "redis-v3":
                type: aws
                config: {}
            
            "postgressql-v96":
                type: aws
                config:
                    automatic_minor_upgrade: true
        
applications:
    datawire-legacy:
        - descriptor: https://raw.githubusercontent.com/datawire/cloud-identity/master/Pibstack.yaml
          docker_tag: 1.0
            
        - descriptor: https://raw.githubusercontent.com/datawire/mrfusion/master/Pibstack.yaml                  
          docker_tag: 1.0
            
        - descriptor: https://raw.githubusercontent.com/datawire/mcp/master/Pibstack.yaml       
          docker_tag: 1.0

```
