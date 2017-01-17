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

clusters:
    local : localhost 
    test  : test.api.k8s.example.org
    prod  : prod.api.k8s.example.org

components:
    redis:
        local: <docker-repo>
        test: <terraform-module>
        prod: <terraform-module>
        
    postgresql-9:
        local: <docker-repo>
        test: <terraform-module>
        prod: <terraform-module>
        
applications:
    datawire-legacy:
        identity: https://github.com/datawire/cloud-identity/master/Pibstack.yaml
        mrfusion: https://github.com/datawire/mrfusion/master/Pibstack.yaml                  
        mcp:      https://github.com/datawire/mcp/master/Pibstack.yaml       

```
