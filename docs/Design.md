# Design Notes

## Initial design

User has an Envfile.yaml, in local disk or git repo, doesn't matter.
Users have a particular directory where each sub-directory is a service; the sub-directory names should match the service names in Envfile.yaml.
Envfile.yaml describes the full system setup - each service, what it depends on, how services are grouped together.
`pib` loads just Envfile.yaml, and can use it + reference to the aggregate directory to do things like "run just this service locally" or "run all services locally".

Just starting out: Envfile.yaml is on local disk.

Later on when more production-y, and adding new service: Envfile.yaml is in git repo. changes to Envfile.yaml happen on a branch. that branch is only merged ... once new service is ready for broader use. commits to code and Envfile.yaml aren't coordinated in same repository.

## Implementation notes

Configuration gets loaded into process.

It is transformed into an abstract representation of configuration (as `pyrsistent` objects probably.)

Those can be transformed into an abstract representation of deployment objects, e.g. k8s objects.

A command plus configuration representation transforms into actions to take.
