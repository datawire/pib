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


def deploy(stack_config, tag_overrides):
    """Start minikube and deploy current config."""
    with open("pib.log", "a+") as logfile:
        run_local = RunLocal(logfile)
        run_local.ensure_requirements()
        run_local.start_minikube()
        run_local.deploy(stack_config, tag_overrides)
        print("Service URL: {}".format(run_local.get_service_url(stack_config)))


def watch(stack_config):
    """
    As code changes, rebuild Docker images for given repos in minikube Docker,
    then redeploy.
    """
    with open("pib.log", "a+") as logfile:
        run_local = RunLocal(logfile)
        run_local.ensure_requirements()
        run_local.start_minikube()
        run_local.set_minikube_docker_env()
        print("Service URL: {}".format(run_local.get_service_url(stack_config)))
        while True:
            tag_overrides = run_local.rebuild_docker_image(stack_config)
            run_local.deploy(stack_config, tag_overrides)
            sleep(20)


USAGE = """\
Usage: pib deploy [name=image-tag ...]
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
    if sys.argv[1] == "deploy":
        deploy(stack_config, dict([s.split("=", 1) for s in sys.argv[2:]]))
    elif sys.argv[1] == "watch":
        watch(stack_config)
    else:
        raise SystemExit("Not implemented yet.")
