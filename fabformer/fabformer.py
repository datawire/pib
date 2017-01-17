from .util import merge_dicts
from os.path import expanduser
from pathlib import Path

fabformer_home = Path(expanduser('~'), '.fabformer')
fabformer_deps = fabformer_home / 'bin'


def fabformer(config_file):
    fabformer_home.mkdir(exist_ok=True)
    fabformer_deps.mkdir(exist_ok=True)

    with open('', 'r') as f:
        import yaml
        config = Config(yaml.load(f))
        return Fabformer(config)


class Config:

    __DEFAULT_STATE_STORE_CONF = {'provider': 's3'}
    __DEFAULT_DNS_CONF = {'provider': 'route53'}

    def __init__(self, raw):
        raw = dict(raw)
        self.state_store = merge_dicts(Config.__DEFAULT_STATE_STORE_CONF, raw.get('state_store', {}))
        self.dns = merge_dicts(Config.__DEFAULT_DNS_CONF, raw.get('dns', {}))

        self.raw = raw

    def state_store_name(self, aws_ctx):

        """Return the name of the Fabformer state store. If the config does not specify a name then a stable name will
        be autogenerated from the aws_ctx"""

        return self.state_store.get('name', 'fabformer-{0}'.format(aws_ctx.account_id))


class Prepare:

    def check(self):
        pass

    def apply(self):
        pass


class Fabformer:

    def __init__(self, config):
        self.config = config

    def dump_config(self):
        from click import echo
        echo(str(self.config.raw))

    def prepare(self):

        """Performs AWS environment preparation.

        The environment
        """
