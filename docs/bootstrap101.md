# Bootstrapping 101

## Prequisites

1. Familiarity with [Git](https://git-scm.com/), [GitHub](https://github.com/), and how [Git branches work](https://git-scm.com/book/en/v2/Git-Branching-Basic-Branching-and-Merging).
2. How to use [Travis-CI](https://travis-ci.org/).
3. How to use [Terraform](https://www.terraform.io/docs/index.html) at a basic level to perform infrastructure provisioning.
4. Access to or the ability to get AWS IAM credentials with superuser capabilities.

## Overview

Pib manages an environment via Git branches; a single git branch in the format `env/$name` maps to a Pib-managed environment. An instantiated environment in Pib is a composition of AWS VPC, Kubernetes cluster, and associated infrastructure components provided by AWS such as an RDS PostgreSQL instance.

## Environment Setup

The process to setup an environment involves laying down a basic AWS networking fabric and then creating a Kubernetes cluster in that networking environment. Pib works by reacting to changes in a GitHub repository so the first step before we do anything is to setup Git and GitHub.

1. Create a new directory your local machine: `mkdir ~/pib/environments`.

2. Change into the environment directory: `cd ~/pib/environments`.

3. Initialize a new Git repository: `git init`.

4. Create a new GitHub project to host the Git repository.

5. Create a new branch in the Git repository named `env/dev`: `git checkout -b env/dev`. Pib seperates environments by using Git branches to maintain state information. 

6. Add the GitHub remote to the environments Git repository: `git remote add origin git@github.com:${YOUR_ORGANIZATION_OR_USERNAME}/${REPO_NAME}.git`. Update the `${...}` segments with the correct information, for example: `git@github.com:datawire/environments.git`

7. Create a new a directory to store Terraform configuration: `mkdir terraform`

8. Change into the terraform directory: `cd terraform/`

9. Create a new Terraform template for the environment: `touch main.tf`

10. Edit the `main.tf` file and add the following information and save afterward:

```hcl
module "environment" {
  source = "github.com/datawire/building-blocks//environment/aws"
  name   = "dev"
}
```
11. Setup a new Travis-CI account.

12. Configure Travis-CI to track the repository on GitHub.

13. Create a `.travis.yml` with the following configuration.

```yaml
dist: trusty
language: generic
sudo: false

cache:
  pip: true
  directories:
  - "${HOME}/bin"

before_install:
- export PATH=$PATH:$HOME/bin
- bin/setup.sh

before_script:
- bin/init.sh

script:
- bin/run.sh

after_success:
- bin/after_success.sh
```

14. Acquire AWS IAM credentials that have superuser capabilities. These permissions will be needed for bootstrapping the environment and then deployment Kubernetes.

**NEED FLESHING OUT BEYOND THIS POINT**

15. Configure Travis with AWS access and secret key

16. Push environment to Travis

17. Generate Terraform configuration for a Kubernetes cluster using Kops

18. Modify the `main.tf` file with the Kubernetes cluster module.

19. Commit the changes to Git and lets Travis run.







