#!/usr/bin/env python3

from pathlib import Path
from time import sleep
import os

import click

from .local import RunLocal
from .stack import StackConfig
from . import __version__

# Pacify Click:
if os.environ.get("LANG", None) is None:
    os.environ["LANG"] = os.environ["LC_ALL"] = "C.UTF-8"


def start():
    """Download and start necessary tools.

    :return: RunLocal instance.
    """
    logfile = open("pib.log", "a+")
    run_local = RunLocal(logfile)
    run_local.ensure_requirements()
    run_local.start_minikube()
    run_local.set_minikube_docker_env()
    return run_local


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
def cli():
    """pib: run a Pibstack.yaml file locally."""


@cli.command("deploy", help="Deploy current Pibstack.yaml.")
def cli_deploy():
    stack_config = StackConfig(Path("."))
    run_local = start()
    redeploy(run_local, stack_config)
    print_service_url(run_local, stack_config)


@cli.command("watch", help="Continuously deploy current Pibstack.yaml.")
def cli_watch():
    stack_config = StackConfig(Path("."))
    run_local = start()
    redeploy(run_local, stack_config)
    print_service_url(run_local, stack_config)
    watch(run_local, stack_config)
