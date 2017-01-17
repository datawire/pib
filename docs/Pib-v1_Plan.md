# Pib v1 - The working software engineer's deployment system

Pib is an attempt to test a hypothesis that a systems-oriented microservices deployment system can be created using many off-the-shelf open source tools and free services. The idea behind Pib is to give developers a toolchain for deploying microservices that has a very small surface area of "things" that need to be learned.

## Pib Bootstrapping

A Pibtastic deployment system needs:

1. A single repository that is public or private and contains a system definition file. The system definition file indicates how applications are composed of microservices and where to find component infrastructure definitions (e.g. a postgresql database config)

2. Each service lives in its own GitHub repository. The repository should contain at a minimum source code and a `Pibstack` (YAML? (for now...)) that contains some information about the service.

## Pibstack

An example for a service that requires its own Redis server.

```yaml
# An image definition defines how to resolve a Docker image. For now it will be as simple as specifying the repo, but could be expanded 
image:
  repository: <docker_repository_string>

# The requires section is saying this service wants a unique purpose-specific piece of infrastructure that is not shared with other services.
requires:
  - redis/redis:4
```

## Sysdef File (for lack of better name)

```yaml
components:
  # Each component specifies how to use it for that environment.
  "redis:v3"
    # point pib to use a Redis docker image hosted somewhere
    dev: docker://redis/redis:3.2
    
    # or reference a Terraform stack. Datawire can provide a lot of nice very common ones similar to how Segment.io works.
    prod: terraform:gh://datawire/building-blocks//elasticache-redis-v3

  "postgresql:v9.6"
    dev: docker://postgresql/postgresql:9.6
    prod: terraform:gh://datawire/building-blocks//rds-postgresql-v96

applications:
  WickedCool:
    services:
    - gh:foocorp/wickedcool-api
    - gh:foocorp/wickedcool-analytics
    - gh:foocorp/wickedcool-admin
    provides:
    - postgresql:v9.6
```

## Flows

### Run the WickedCool application which consists of `wicked-api`, `wickedcool-analytics`, `wickedcool-admin`.

```bash
cd ~/workspace

# stealing the "gh:" shorthand for github from the cookiecutter project 
pib-local load gh://foocorp/sysdef

# clones or updates out all the repositoriess associated with the wickedcool project
pib-local get wickedcool

# run the wickedcool app locally
pib-local run wickedcool
```

### Deploy the WickedCool application

## Mechanical Stuff

This section is just loosely documenting some mechanical challenges and solutions we discussed yesterday

### Pib creates AWS infrastructure, but how do we expose that infrastructure to Kubernetes-run containers?

Pib via Terraform goes off and creates things like RDS instances. Information such as the RDS URL, username and password need to be provided to things running on the cluster to be useful.

Terraform stores state information in S3. The best way to handle this then is to have a small service that runs on the Kubernetes cluster which reads the Terraform state and then injects it into running services as a Kubernetes ConfigMap or Secret (an RDS URL probably should also be injected as an ExternalService).

Accessing the Terraform state in S3 is trivial because the Kubernetes nodes should have the necessary IAM config to just read with authorized access. 
