# Pib

Pib lets you develop services as systems, develop locally quickly, and be confident they will run the same way in production while still letting you customize the production setup appropriately.

## Quickstart

Let's say you have a repository with your web service.
It has a `Dockerfile` that lets you run it in isolation (`docker run examplecom/yourapp`), but it also needs a database to be functional.

Let's codify that relationship by creating a `Pibstack.yaml` in your service's git repository:

```yaml
---
pibstackVersion: 1

name: hello

image:
  repository: examplecom/yourapp
  port: 5100

expose:
  path: /hello

requires:
  - template: postgres
    type: component
    image: "postgres:9.6"
    config:
      port: 5432
```

Now in your service's git repository you can run:

```console
$ pib watch &
```

This will:

1. Automatically build a Docker image of your application using your `Dockerfile`.
2. Run your application and its dependencies, in this case PostgreSQL, inside a local Kubernetes setup.
3. As you change your code the containers will be updated with the latest version of the code.

Your application code can find the address the of the PostgreSQL server by looking at the environment variables `POSTGRES_COMPONENT_HOST` and `POSTGRES_COMPONENT_PORT`.
In general the environment variables are of the form `<template>_COMPONENT_HOST/PORT` where `template` is the template chosen in the requirement.

Notice that the configuration isn't just saying "I need this Docker image as a dependency."
In addition to specifying an image it also tells you that it's using PostgreSQL (`template: postgres`).

Pib also supports system-level configuration that overrides that template so that it can be used in different ways in different environments.
For example, you can configure `template: postres` to run the production PostgreSQL using AWS RDS.

The goal of the Pib stack is to allow you to run your service as a whole, sharing the same configuration but allowing you to use the appropriate technology for local development vs. production.

## What is Pib?

Pib is a toolchain for easily running and deploying modern services, from web applications to microservices.

A modern service doesn't include just business logic: it might need a database, a cache, or other supporting processes.
Source code is therefore not enough to run the service, you need all the dependencies running as well.

A Pib stack configuration for your service allows you to:

1. Run your code and its dependencies locally, with support for a quick feedback loop.
   Local runtime is in a production-like local Kubernetes cluster (using minikube).
2. Use the same configuration to run your service in production.
   While Pib builds on modern container technology like Docker and Kuberentes, it does not lock you in to that ecosystem for production usage.
   For example, you can use Pib to create a AWS RDS database for production use.

This repository includes the local developer-environment toolchain for Pib.
Production use is a work-in-progress by Datawire Inc: [get in touch](https://www.datawire.io/contact/) if you want to learn more.

## Installation

To build and install:

```console
$ pip install tox
$ tox -e py3
$ cp dist/pib $HOME/bin  # or some other place in $PATH
```

`pib` will install `minikube` and `kubectl` when it first runs, you don't need to install them yourself.

TODO: better installation instructions.

## Developer Information

### Hacking Setup

This is the super painless way to get started hacking in a virtualenv configured for development.

```bash
make venv
source venv/bin/activate
pip install -e .
```

### Running Tests

Be a good developer and run tests before committing :)

```bash
tox -e py3
```

## License

Project is open-source software licensed under **Apache 2.0**. Please see [LICENSE](LICENSE) for further details.
