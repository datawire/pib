"""Code for parsing the Envfile."""

from yaml import safe_load

# Until we have a schema and can use, use an python-jsonschema-objects, just
# use a thing that turns dictionaries into objects with attributes:


class AttrDict(dict):
    """Convert attribute lookups into key lookups."""
    def __getattr__(self, k):
        value = self[k]
        if isinstance(value, dict):
            value = AttrDict(value)
        return value


def load_env_file(path_to_repo):
    """Load Envfile from path, return AttrDict."""
    with (path_to_repo / "Envfile.yaml").open() as f:
        return AttrDict(safe_load(f.read()))
