# Environments.pib

The `Envfile` (for lack of better name) contains the system definition.

## Specification

### Serialization

An Envfile file is stored and transmitted as a single YAML document that **MUST BE** JSON serializable. In practice this means YAML-specific features such as multiple documents per file is not allowed.

### Naming

An Envfile file must be named `Envfile.yaml`.

### Structure

An Envfile is composed of a root YAML dictionary that contains nested dictionaries and lists.

1. The root MUST have a field `Envfile-version:` `(type: Int)` which indicates the version of the specification used.

TODO: ... redo with latest version, based on schema.
