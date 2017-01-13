#!/usr/bin/env python3

from pathlib import Path
from time import sleep
# import os
import sys

# import click

from .local import RunLocal
from .stack import StackConfig

# Pacify Click:
# if os.environ.get("LANG", None) is None:
#    os.environ["LANG"] = os.environ["LC_ALL"] = "C.UTF-8"


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
    print("Service URL: {}".format(run_local.get_service_url(stack_config)))


def watch(run_local, stack_config):
    """
    As code changes, rebuild Docker images for given repos in minikube Docker,
    then redeploy.
    """
    while True:
        sleep(20)
        redeploy(run_local, stack_config)


USAGE = """\
Usage: pib deploy
       pib watch
       pib --help

Make sure you are in same directory as a Pibstack.yaml file.
"""


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print(USAGE, file=sys.stderr)
        sys.exit(1)
    if sys.argv[1] == "--help":
        print(USAGE, file=sys.stderr)
        sys.exit(0)
    stack_config = StackConfig(Path("."))
    run_local = start()
    if sys.argv[1] == "deploy":
        redeploy(run_local, stack_config)
        print_service_url(run_local, stack_config)
    elif sys.argv[1] == "watch":
        redeploy(run_local, stack_config)
        print_service_url(run_local, stack_config)
        watch(run_local, stack_config)
    else:
        raise SystemExit("Not implemented yet.")
