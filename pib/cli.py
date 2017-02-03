#!/usr/bin/env python3

from functools import wraps
from pathlib import Path
from time import sleep
from sys import stdout, exit
import os

import click
from yaml import safe_load

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
        # Wipe existing logfile, and use line buffering so data gets written
        # out immediately.
        logfile = open(logfile_path, "w", buffering=1)
    return RunLocal(logfile, click.echo)


def start(logfile_path):
    """Download and start necessary tools.

    :return: RunLocal instance.
    """
    run_local = create_run_local(logfile_path)
    run_local.ensure_requirements()
    run_local.start_minikube()
    run_local.set_minikube_docker_env()
    return run_local


def load_envfile(config_path):
    """Load an Envfile.yaml into a envfile.System given a Path."""
    try:
        with config_path.open() as f:
            return _load_envfile(safe_load(f.read()))
    except ValidationError as e:
        click.echo("Error loading Envfile.yaml:")
        for error in e.errors:
            click.echo("---\n" + error)
        exit(1)


def redeploy(run_local, envfile, services_directory):
    """Redeploy currently checked out version of the code."""
    tag_overrides = run_local.rebuild_docker_images(
        envfile, services_directory)
    run_local.deploy(envfile, tag_overrides)


def print_service_url(run_local, envfile):
    """Print the service URL."""
    services, application_url = run_local.get_application_urls(envfile)
    for name, url in services.items():
        click.echo("{}: {}".format(name, url))
    click.echo("Main application: {}".format(application_url))


def watch(run_local, envfile, services_directory):
    """
    As code changes, rebuild Docker images for given repos in minikube Docker,
    then redeploy.
    """
    while True:
        # Kubernetes apply -f takes 20 seconds or so. If we were to redeploy
        # more often than that we'd get an infinite queue.
        sleep(20)
        redeploy(run_local, envfile, services_directory)


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
param_envfile = click.argument(
    "ENVFILE_PATH",
    type=click.Path(
        readable=True, dir_okay=False, exists=True))


def handle_unexpected_errors(f):
    """Decorator that catches unexpected errors."""

    @wraps(f)
    def call_f(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            click.echo(
                "Looks like there's a bug in our code. Sorry about that!\n")
            click.echo(
                click.style(
                    "We'd really appreciate it if you could file an issue at ",
                    bold=True) + click.style(
                        "https://github.com/datawire/pib/issues/new",
                        bold=True,
                        underline=True) + click.style(
                            " with the following information:", bold=True))
            click.echo("""\

1. The command you ran.
2. The output of `pib --version`.
3. The traceback and error printed below.
4. The contents of your pib.log file (it should be in the current directory).
5. Your Envfile.yaml if you're OK sharing it.

Here's the traceback and error from the code:
""")
            raise

    return call_f


@click.group()
@click.version_option(version=__version__)
def cli():
    """pib: run a Pibstack.yaml file locally."""


@cli.command("deploy", help="Deploy current Pibstack.yaml.")
@opt_logfile
@opt_directory
@param_envfile
@handle_unexpected_errors
def cli_deploy(logfile, directory, envfile_path):
    envfile = load_envfile(Path(envfile_path))
    directory = Path(directory)
    run_local = start(logfile)
    redeploy(run_local, envfile, directory)
    print_service_url(run_local, envfile)


@cli.command(
    "watch",
    help="Continuously deploy application specified " + "by Envfile.yaml.")
@opt_logfile
@opt_directory
@param_envfile
@handle_unexpected_errors
def cli_watch(logfile, directory, envfile_path):
    envfile = load_envfile(Path(envfile_path))
    directory = Path(directory)
    run_local = start(logfile)
    redeploy(run_local, envfile, directory)
    print_service_url(run_local, envfile)
    watch(run_local, envfile, directory)


@cli.command("wipe", help="Wipe all locally deployed services.")
@opt_logfile
@click.confirmation_option(prompt='Are you sure you want to delete everything'
                           ' deployed to your local Kubernetes server '
                           '(minikube)?\nThis will also delete services not '
                           'started by pib.')
@handle_unexpected_errors
def cli_wipe(logfile):
    run_local = start(logfile)
    run_local.wipe()
    click.echo("Wiped!")


def main():
    cli()  # pylint: disable=E1120,E1123
