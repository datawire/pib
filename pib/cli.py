#!/usr/bin/env python3

from pathlib import Path
from time import sleep
from sys import stdout, exit
import os

import click

from .local import RunLocal
from .stack import StackConfig
from .schema import ValidationError
from . import __version__

# Pacify Click:
if os.environ.get("LANG", None) is None:
    os.environ["LANG"] = os.environ["LC_ALL"] = "C.UTF-8"


def start(logfile_path):
    """Download and start necessary tools.

    :return: RunLocal instance.
    """
    if logfile_path == "-":
        logfile = stdout
    else:
        logfile = open(logfile_path, "a+")
    run_local = RunLocal(logfile)
    run_local.ensure_requirements()
    run_local.start_minikube()
    run_local.set_minikube_docker_env()
    return run_local


def load_stack_config(config_path):
    """Load a StackConfig."""
    try:
        return StackConfig(Path(config_path))
    except ValidationError as e:
        click.echo("Error loading Pibkstack.yaml:")
        for error in e.errors:
            click.echo("---\n" + error)
        exit(1)


def redeploy(run_local, stack_config):
    """Redeploy currently checked out version of the code."""
    tag_overrides = run_local.rebuild_docker_image(stack_config)
    run_local.deploy(stack_config, tag_overrides)


def print_service_url(run_local, stack_config):
    """Print the service URL."""
    click.echo("Service URL: {}".format(
        run_local.get_service_url(stack_config)))


def watch(run_local, stack_config):
    """
    As code changes, rebuild Docker images for given repos in minikube Docker,
    then redeploy.
    """
    while True:
        # Kubernetes apply -f takes 20 seconds or so. If we were to redeploy
        # more often than that we'd get an infinite queue.
        sleep(20)
        redeploy(run_local, stack_config)


@click.group()
@click.version_option(version=__version__)
@click.option("--logfile", nargs=1, type=click.Path(writable=True,
                                                    allow_dash=True,
                                                    dir_okay=False),
              default="pib.log",
              help=("File where logs from running deployment commands will " +
                    "be written. '-' indicates standard out. Default: pib.log"))
@click.option("--directory", nargs=1, type=click.Path(readable=True, file_okay=False,
                                                      exists=True),
              default=".",
              help=("Directory where Pibstack.yaml and Dockerfile can be " +
                    "found. Default: ."))
@click.pass_context
def cli(ctx, logfile, directory):
    """pib: run a Pibstack.yaml file locally."""
    ctx.obj["logfile"] = logfile
    ctx.obj["directory"] = directory


@cli.command("deploy", help="Deploy current Pibstack.yaml.")
@click.pass_context
def cli_deploy(ctx):
    stack_config = load_stack_config(Path(ctx.obj["directory"]))
    run_local = start(ctx.obj["logfile"])
    redeploy(run_local, stack_config)
    print_service_url(run_local, stack_config)


@cli.command("watch", help="Continuously deploy current Pibstack.yaml.")
@click.pass_context
def cli_watch(ctx):
    stack_config = load_stack_config(Path(ctx.obj["directory"]))
    run_local = start(ctx.obj["logfile"])
    redeploy(run_local, stack_config)
    print_service_url(run_local, stack_config)
    watch(run_local, stack_config)


def main():
    cli(obj={})  # pylint: disable=E1120,E1123
