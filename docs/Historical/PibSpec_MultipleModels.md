# Pib Cloud 

The `pib cloud apply` command (to be chosen) is the part of `pib` that handles the deployment and continued management of an applications cloud resources (e.g. RDS backed PostgreSQL databases, S3 buckets, or Elasticache Redis components among other things).

## Envfile

The `pib cloud` functionality relies on the concept of an Envfile. The Envfile is a declaration of how `Environments` and `Applications` are composed when they are run in different setups such as local or remote. The basic premise of `pib cloud apply` is that an Envfile is inspected and then the program goes off and applies any changes to the environment. In the case of a remote system such as one running on Amazon Web Services ("AWS") this means that AWS resources will be created, modified or destroyed per each run.

## Design A

Consider an Envfile that looks like this (note the YAML doc structure is still in design so this is hypothetical):

```yaml
environments:
  local:
    address: localhost
    components:
      "redis-v3":
        type: docker
        image: redis/redis:3
        config: {}
                
      "postgresql-v96":
        type: docker
        image: postgres/postgres:9.6
        config: {}
                
  cloud:
    address: prod.api.k8s.example.org
    components:
      "redis-v3":
        type: aws
        module: file://terraform/elasticache_redis
            
      "postgresql-v96":
        type: aws
        module: file://terraform/rds_postgresql
        
applications:
  helloworld:
    - descriptor: https://raw.githubusercontent.com/datawire/helloworld/master/Pibstack.yaml
      docker_tag: 1.0
    
    - redis-v3
    - postgresql-v96
```

We can ignore the `environments.local` block for the remander of this section as it was only included to provide context. In the `environments.cloud` section we see two component definitions, one for a PostgreSQL 9.6 database and the other for a Redis v3 key/value store. Definitions are reuseable configurations that applications (e.g. `helloworld`) specify as requirements. What this means is that these are defined configurations for piece of infrastructure that can be created on the remote AWS system. Infrastructure component definitions are written for use with Hashicorps [Terraform](https://terraform.io) tool which means we have immediate access to manage a large library of cloud provider resources (both AWS and others) without us having to write large amounts of code to create and manage resources ourselves.

In this design applications such as `helloworld` consume infrastructure definitions, for example, `helloworld` declares that it needs a `redis-v3` and `postgresql-v96` database to be run. When the `helloworld` application is deployed via `pib cloud apply` then in the best case the necessary Terraform template would be generated behind the scenes and *automagically* applied for the end-user without them knowing.

### Considerations for this Design

The main consideration for this design is reducing friction to **bootstrap** deployment as much as possible for some definition of "friction". At the highest level it exposes two concepts:

1. A persistent declaration of a system.
2. A command for actualizing the entire declaration.

The tool is supposed to be a bit *magical* in the way it operates and doesn't expose too many details to the application developer. This is both a good thing and a bad thing.

### Tradeoffs and Consequences of this Design

The major trade-off for this design is that when the state of application and consequently an environment change or do not fit perfectly into a mental model of AWS then it is a leaky abstraction that starts to expose details about Terraform and AWS in ways that are unpredictable or confusing because they were previously hidden. Further the model gets the "lifetime" of resources incorrect.

I'm not asserting that all of these are major issues though I feel strongly like `<2>` followed by `<1>` are good reasons why this model is very flawed.

#### <1> Terraform implementation details

Terraform works using a `plan -> apply` model for rolling out changes to infrastructure. When something changs in a Terraform configuration the tool notifies the user and expects them to review the changes before invoking the `apply` step. This is done so that potentially dangerous operations are not run without the user consenting to the change, for example, it would be very bad if a database with production data were destroyed accidentally during a run because a user carelessly modified the name of the application or removed a declaration of the database from an application, for example, consider either of these scenarios:

**ORIGINAL**

```yaml
applications:
  helloworld:
    - descriptor: https://raw.githubusercontent.com/datawire/helloworld/master/Pibstack.yaml
      docker_tag: 1.0
    
    - redis-v3
    - postgresql-v96
```

**ACCIDENTAL RENAME**

```yaml
applications:
  hellworld:
    - descriptor: https://raw.githubusercontent.com/datawire/helloworld/master/Pibstack.yaml
      docker_tag: 1.0
    
    - redis-v3
    - postgresql-v96
```

**AcCIDENTAL REMOVAL**

```yaml
applications:
  hellworld:
    - descriptor: https://raw.githubusercontent.com/datawire/helloworld/master/Pibstack.yaml
      docker_tag: 1.0
    
    - redis-v3
```

#### <2> This model gets "lifetime" of backend infrastructure very wrong

Backend infrastructure such as database servers, blob storage buckets (S3), queue servers etc. have an undefined or "infinite" lifetime in a "production" or non-development context because those systems hold customer data. Applications have shorter, more finite lifespans. Business logic comes and goes and it is dangerous to expose to the developer the idea that their persistence and application are tied to together tightly. Going back to the above shown Envfile with the `applications.helloworld`, if the `helloworld` app were decomissioned what would happen to that database when the subsequent lines were removed from the configuration? The answer is that the database would be terminated and all that customer data would be lost.

#### <3> Bad fit for teams that have existing cloud deployments.

Terraform wants to own the entire infrastructure definition of a system. The tool is puroposely designed for this use-case and many companies when they actually adopt Terraform explicitly go through the effort of converting all their infrastructure definitions over to use the tool or they segment their stack between pre-Terraform and post-Terraform deployed bits. Very recently Hashicorp has started adding limited support for importing existing infrastructure into Terraform but it is still a WIP.

But why is it actually a bad fit for existing infrastructure? Terraform works by building out a data model of all infrastructure used and then constructing a dependency graph between the resources that are defined or known. Imagine now if an implicitly relied upon dependency is removed, for example, a Route 53 DNS record such as (datawire.io). Terraform will fail to work as expected without manual intervention if that record is removed via the AWS CLI or console. "Fail to work as expected" in this case means one of two things:

1. The Terraform plan stage will fail because the operation is fundamentally impossible... this could occur if the resource was required.

2. The Terraform plan stage will plan "successfully" in the sense that it knows how to reconcile the change, perhaps by disassociating something, however, this is not likely what the developer expects.

An answer could be "Do not use Terraform" and that's an option but it's absolutely the best-in-class tool for this problem because it has a ton of users, is actively developed, knows how to handle in many cases AWS eventual consistency issues, and knows how to deploy pretty much every resource under the sun in AWS and other major cloud providers or tools.

#### <4> AWS implementation details (or really any cloud provider)

Examples of this include:

1. Database instance sizing (which one do I need? t2.db.micro requires reading AWS docs. Something like "small" | "normal" | "large" hides too many details about performance and cost.

2. How to handle situations like security and IAM correctly.

3. I want to use AWS Elasticsearch and it needs to be in a private subnet with a NAT but my VPC does not have either of these and I don't know how to make that happen.

#### <5> Potentially very expensive without realizing!

This model hides infrastructure definitions because it does a bunch of Terraform magic in the background. Developers will be led to believe some of this infrastructure is cheap, but we have firsthand experience that tells us this is not the case, for example, consider out recent discovery about the price of NAT gateways.
It's dangerous to just put a one or two line config in front of a developer and teach them that this is a "good" approach only for them to find out six months later that they're hemmoraghing the engineering budget for their service and now signifigant effort needs to be spent to establish a new cheaper architecture. What felt free with Docker containers on Kubernetes is likely very expensive when actually using a cloud provider such as AWS.

#### <6> Tightly coupled to Terraform

Goes without saying this model requires using Terraform for orchestration and doesn't allow adoption of in breed technologies, using other systems, or easily adapting to custom models.

### Final Thoughts on Design A

For what it is worth there is already some historical precedent that has been set that agrees with the premise that this is a leaky abstraction. Hashicorp's own product [Otto](https://www.hashicorp.com/blog/otto.html) was a similar attempt to build a product that did this and it was deep-sixed due to the complexity of merging an app-centric and infrastructure-centric worldview together (among other things).

## Design B

Consider an Envfile that looks like this (tenative YAML doc structure):

```yaml
environments:
  local:
    address: localhost
    components:
      "redis-v3":
        type: docker
        image: redis/redis:3
        config: {}
                
      "postgresql-v96":
        type: docker
        image: postgres/postgres:9.6
        config: {}
        
  cloud:
    address: cloud.k8s.example.org  
    state: terraform:s3://environments/cloud.tfstate
      
applications:
  helloworld:
    services:
      - descriptor: https://raw.githubusercontent.com/datawire/helloworld/master/Pibstack.yaml
        docker_tag: 1.0
    
    requires:
      - redis-v3
      - postgresql-v96
```

We can ignore the `environments.local` block for the remander of this section. The `environments.cloud` section there is a key `state` that points at a remotely stored Terraform statefile in an S3 bucket. Infrastructure definitions **are not** defined in the Envfile anymore. Instead we will rely on using native Terraform definitions to handle deploying infrastructure (similar to segment.io model).

In this design applications such as `helloworld` consume infrastructure definitions, for example, `helloworld` declares that it needs a `redis-v3` and `postgresql-v96` database to be run. When the `helloworld` application is deployed via `pib cloud apply` the model **IS NOT** to deploy the necessary infrastructure like as defined in Design A but rather that the system verifies such things are available within the environment before attempting to deploy the application. If the things are not defined then errors out and hopefully provides a useful piece of context about what is missing. Similarly during this time if the necessary infrastructure is found then the required Kubernetes ConfigMaps or Secrets are injected by reading the infrastructure state definition that was pointed to in the `environment.cloud.state` key.

### Considerations for this Design

This design attempts to make bootstrapping easy but also makes infrastructure definition slightly more explicit by requiring the explicit use of Terraform. With this in mind there is more friction but I believe it is "good" friction in the sense that it promotes correct separation of concerns between definition, provisioning, and fulfilling requirements. To this end the primary goals of this system are: 

1. A persistent declaration of the components needed in a environment to replicate a system.
2. A command to apply changes to applications constituent components (e.g. upgrade `helloworld` from 1.0 -> 1.1).
3. That when the `apply` command is run then the tool ensures the required components are (1) running and (2) injected into the configuration of the application such that `helloworld` can find and communicate with `redis-v3` and `postgresql-v96`.

With regards to making Terraform "easy" the idea is to provide a segment.io-like stack of well-designed, easy to consume building blocks along with easy to consume documentation about how to use those building blocks to achieve infrastructure provisioning.

### Tradeoffs and Consequences of this Design

The major trade-off for this design is that it's a multi-component design. It's not trying to hide Terraform as the default infrastructure orchestration component so there is some additional friction in requiring that developers learn this tool. On the other hand I think this can be made simple.

### Additional Benefits of this Design

## Decoupled from Cloud Provider

We don't need to try and pretend to know how to wire up Terraform configuration correctly to make this system work. I believe I can replicate most of the Logrocket configuration which has multiple Cloud provider dependencies.

## Decoupled from Terraform

Because the system reads state files as long as we can write a statefile parser for a tool (of which we can for Terraform) then we can inject configuration into our system. This means we can adapt to Terraform, CloudFormation, Ansible, or any other tool that exists or comes into existence.
