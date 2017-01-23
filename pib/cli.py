#!/usr/bin/env python3

from pathlib import Path
from time import sleep
from sys import stdout, exit
import os

import click

from .local import RunLocal
from .schema import ValidationError
from .envfile import load_envfile as _load_envfile
from . import __version__

# Pacify Click:
if os.environ.get("LANG", None) is None:
    os.environ["LANG"] = os.environ["LC_ALL"] = "C.UTF-8"


def create_run_local(logfile_path):
    """
    :return: RunLocal instance for the given logfile path.
    """
    if logfile_path == "-":
        logfile = stdout
    else:
        logfile = open(logfile_path, "a+")
    return RunLocal(logfile)


def start(logfile_path):
    """Download and start necessary tools.

    :return: RunLocal instance.
    """
    run_local = create_run_local(logfile_path)
    run_local.ensure_requirements()
    run_local.start_minikube()
    run_local.set_minikube_docker_env()
    run_local.update_environment()
    return run_local


def load_envfile(config_path):
    """Load an Envfile.yaml."""
    try:
        return _load_envfile(Path(config_path))
    except ValidationError as e:
        click.echo("Error loading Envfile.yaml:")
        for error in e.errors:
            click.echo("---\n" + error)
        exit(1)


def redeploy(run_local, envfile, service_directory):
    """Redeploy currently checked out version of the code."""
    tag_overrides = run_local.rebuild_docker_images(envfile, service_directory)
    run_local.deploy(envfile, tag_overrides)


def print_service_url(run_local):
    """Print the service URL."""
    click.echo("Application URL: {}".format(run_local.get_application_url()))


def watch(run_local, envfile, service_directory):
    """
    As code changes, rebuild Docker images for given repos in minikube Docker,
    then redeploy.
    """
    while True:
        # Kubernetes apply -f takes 20 seconds or so. If we were to redeploy
        # more often than that we'd get an infinite queue.
        sleep(20)
        redeploy(run_local, envfile, service_directory)


opt_logfile = click.option(
    "--logfile",
    nargs=1,
    type=click.Path(
        writable=True, allow_dash=True, dir_okay=False),
    default="pib.log",
    help=("File where logs from running deployment commands will " +
          "be written. '-' indicates standard out. Default: pib.log"))
opt_directory = click.option(
    "--directory",
    nargs=1,
    type=click.Path(
        readable=True, file_okay=False, exists=True),
    default=".",
    help=("Directory where services can be found. Default: ."))
opt_envfile = click.option(
    "--envfile",
    nargs=1,
    type=click.Path(readable=True, dir_okay=False, exists=True),
    help=("Path to Envfile.yaml.")
    )


@click.group()
@click.version_option(version=__version__)
def cli():
    """pib: run a Pibstack.yaml file locally."""


@cli.command("deploy", help="Deploy current Pibstack.yaml.")
@opt_logfile
@opt_directory
@opt_envfile
def cli_deploy(logfile, directory, envfile):
    envfile = load_envfile(Path(envfile))
    directory = Path(directory)
    run_local = start(logfile)
    redeploy(run_local, envfile, directory)
    print_service_url(run_local)


@cli.command("watch", help="Continuously deploy application specified " +
             "by Envfile.yaml.")
@opt_logfile
@opt_directory
@opt_envfile
def cli_watch(logfile, directory, envfile):
    envfile = load_envfile(Path(directory))
    directory = Path(directory)
    run_local = start(logfile)
    redeploy(run_local, envfile, directory)
    print_service_url(run_local)
    watch(run_local, envfile, directory)


@cli.command("wipe", help="Wipe all locally deployed services.")
@opt_logfile
@click.confirmation_option(prompt='Are you sure you want to delete everything'
                           ' deployed to your local Kubernetes server '
                           '(minikube)?\nThis will also delete services not '
                           'started by pib.')
def cli_wipe(logfile):
    run_local = start(logfile)
    run_local.wipe()
    click.echo("Wiped!")


def main():
    cli()  # pylint: disable=E1120,E1123
