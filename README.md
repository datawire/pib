# Pib

## Motivation

### Modern applications are systems

Many modern applications are a system, composed of a number of business logic *services*.

For example, you might be building a website that has multiple services: a main one for HTTP and a secondary one for pushing WebSocket events to the browser.
Or you might be building a data ingestion pipeline: one service accepts events and pushes them to a database or queue, and other services read that data from the database/queue.

Each service might rely on a number of *resources*, things like PostgreSQL, Redis, ElasticSearch or Kafka.
Some resources might only be used by a single service, and some might be shared.

### Developing and deploying systems is harder

Developing these modern applications introduces new problems:

* How do you spin up a service and its dependencies, or the whole system, for local development?
  Tools like Docker Compose help, but they usually can't be used to describe your production system.
* How do you spin up a service and its dependencies in a production environment?
  Tools like Terraform can deploy your infrastructure, but won't help with local development.
* How do you deal with a combination of container infrastructure and cloud infrastructure?
  Deploying to both Kubernetes and AWS in sync can be difficult.

### Pib: an end-to-end solution

Pib provides a way for you to describe your application and the services that compose it as a system.
Once you've written that description you have a single coherent, system-level view of your application.
And you can use this single description both for local development and, with additional configuration, for production deployments.

That means:

* You can develop locally with a fast feedback loop.
* Your production environment can use infrastructure like AWS RDS.
* You can trust that local development and production are still as similar as possible, because they both run off the same system-level description..

## Warning: work-in-progress, changing rapidly

## Quickstart

Let's say you have a repository with one of your web services.
It has a `Dockerfile` that lets you run it in isolation (`docker run examplecom/hello`), but it also needs a database to be functional.
You put a Git checkout of that repository in `~/pib`:

```console
you@yourlaptop:~/pib $ git clone git@github.com:examplecom/hello.git
you@yourlaptop:~/pib $ ls -l hello/Dockerfile 
-rw-rw-r-- 1 you you 2561 Jan  4 16:00 hello/Dockerfile
```

You can now codify the system's overall shape by creating a `Envfile.yaml`.
For now we'll create it in `~/pib`, but for production-use you'd want the config in its own version control repository.

Initially you just have a simple system-level config: a single service (`hello`, to match its directory name) with a single required component.
Later you can add more services, shared components, and more.

```yaml
Envfile-version: 1

application:
  requires: {}
  services:
    hello:  # <-- this matches the directory name your service is in
      image:
        repository: examplecom/hello
        tag: "1.0"
      port: 5100
      expose:
        path: /  # <-- service will be exposed on root directory
      requires:
        hello-db:
          # Locally we'll use a Docker image (see
          # /local/templates/postgresql-v96 below), but when the time comes to
          # set up production you can can use AWS RDS or other production-grade
          # infrastructure.
          template: postgresql-v96

local:
  templates:
    "postgresql-v96":
      type: docker
      image: postgres:9.6
      config:
        port: 5432

# 'remote' isn't setup now, but we'll add it in later when we're ready to deploy
# to production.
```

Notice that the configuration isn't just saying "I need this Docker image as a dependency."
In addition to specifying an image it also tells you that it's using PostgreSQL (`template: postgresql-v96`).
When you start thinking about production use you could configure the production setup to use AWS RDS instead of a Docker image.

Now you can deploy your whole system in development mode:

```console
you@yourlaptop:~/pib$ pib watch Envfile.yaml &
```

This will:

1. Automatically build a Docker image of your service using your `Dockerfile`.
2. Run your application and its dependencies, in this case PostgreSQL, inside a local Kubernetes setup.
3. As you change your code the containers will be updated with the latest version of the code.

Your service code can find the address the of the PostgreSQL server by looking at the environment variables `HELLO_DB_COMPONENT_HOST` and `HELLO_DB_COMPONENT_PORT`.
In general the environment variables are of the form `<template>_COMPONENT_HOST/PORT` where `template` is the template chosen in the requirement.

### Multiple services

Pib allows you define multiple services for your application, each with its own private required components.
You can also share components across services.
In the following example `Envfile.yaml` you can see two services that share the same ElasticSearch:

```yaml
Envfile-version: 1

application:
  requires:
    logs-es: # <--- this component will be accessible to all services
      template: elasticsearch
  services:
    service-a:
        repository: examplecom/service-a
        tag: "1.0"
      port: 5100
      expose:
        path: /a
      requires:
        hello-db:
          template: postgresql-v96
    service-b:
      image:
        repository: examplecom/service-b
        tag: "1.2"
      port: 80
      expose:
        path: /b
      requires: {}

local:
  templates:
    "postgresql-v96":
      type: docker
      image: postgres:9.6
      config:
        port: 5432
    elasticsearch:
      type: docker
      image: elasticsearch:latest
      config:
        port: 9200
```

### Production

So far we've seen configuration for local development only.
But Pib allows you to use the same configuration to run your services in your operational environments... while allowing you to use the infrastructure of your choice.
While Pib builds on modern container technology like Docker and Kuberentes, it does not lock you in to that ecosystem for production usage.
For example, you can use Pib to create a AWS RDS database for production use.

The way this works is by hooking up the `application` configuration in the `Envfile.yaml` to a tool that is built on Terraform.
This tool is triggered commits to the Git repository where the `Envfile.yaml` sits:

1. It deploys the necessary infrastructure using Terraform (e.g. new AWS RDS).
2. It injects the location of this infrastructure into Kubernetes.
3. It deploys the services to your production Kubernetes cluster, using the image tags from the configuration.

The CI pipelines for individual services can update the tag in this repository whenever a new version is built.
Here is a sample workflow:

1. Code is changed in `hello` git repo and merged to `master`.
2. The `hello` CI tool rebuilds the `examplecom/hello` Docker image with a new tag, pushes it to the Docker registry and then updates the `Envfile.yaml` in the `pib-environments` repository with the new tag.
3. This triggers a CI build on `pib-environments` which calls `pib-cloud`, which redeploys to AWS infrastructure using Terraform, and to Kubernetes using the new service.

### Multiple environments

You might have multiple operational environments.
For example, one for paid customers and one for free users, or one staging and one production.
Pib supports this by having multiple branches in the `pib-environments` git repository, e.g. `environments/production` and `environments/staging`.

## More about Pib

Pib is a toolchain for easily running and deploying modern services, from web applications to microservices.

A modern service doesn't include just business logic: it might need a database, a cache, or other supporting processes.
Source code is therefore not enough to run the service, you need all the dependencies running as well.

A pib configuration for your services allows you to:

1. Run a single service and its dependencies locally, with support for a quick feedback loop.
   Local runtime is in a production-like local Kubernetes cluster (using minikube).
2. Run all the multiple services that compose your application together, spinning up a fully functional application.

Features include:

* Per-service component configuration.
* Shared components for your services.
  E.g. perhaps you have one service that writes to PostgreSQL and another that reads from the same PostgreSQL.
* Support multiple environments by having different branches in the git repository where the `Envfile.yaml` is stored.
  E.g. you can have a staging and production setup.
* Automatic deploys to remote environments (e.g. production Kubernetes on AWS).

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
