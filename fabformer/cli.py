#!/usr/bin/env python3
from . import __version__
from .aws import init_aws_ctx
from .util import load_config
from pathlib import Path
import click
import os

aws = init_aws_ctx()


@click.group()
@click.version_option(version=__version__)
def cli():
    """fabformer

    Forms infrastructure in magical ways to provide Kubernetes-centric fabrics on AWS.
    """


# TODO: This goes away eventually.
@cli.command('debug', help='Print information from the current fabformer repo')
def info():
    click.echo('AWS Account ID: {}'.format(aws.account_id))


@cli.command('init', help='Initialize a new fabformer repository')
def init():
    fab_conf = load_config(Path(os.getcwd()) / 'fabformer.yaml', required=False)
    if fab_conf:
        click.echo('Fabformer is already initialized!')
        return

    cluster_base_domain = click.prompt('Fabric Cluster Domain')

    cfg = {
        'provider': {'region': 'us-east-1'},    # TODO(plombardi): MUST be configurable
        'dns': {'domain': cluster_base_domain}
    }

    with (Path(os.getcwd()) / 'fabformer.yaml').open('w+') as f:
        import yaml
        yaml.dump(cfg, f, default_flow_style=False)

    click.echo("Fabformer initialized!\n")
    click.echo("Run:\n\tgit add fabformer.yaml && git commit -m 'fabformer: initialized basic config'\n")


@cli.command('generate', help='Generate raw configs')
def generate():
    cfg = load_config(Path(os.getcwd()) / 'fabformer.yaml')
    if not cfg:
        click.echo('Fabformer is not initialized!')
        return

    from .fabformer import Generator
    gen = Generator(cfg.get('dns').get('domain'), cfg.get('fabrics', {}))
    gen.generate()


@cli.command('apply', help='Apply fabric configuration')
def apply():
    pass


if __name__ == '__main__':
    cli(prog_name='fabformer')  # pylint: disable=E1123
