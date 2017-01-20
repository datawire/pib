# User Journeys

## The journeys

### NewService: Developing a new service

As a developer I am building a new service in an existing system.
It goes through the following stages:

1. I am building it in isolation; I am not yet thinking about interacting with other components.
2. I am interacting with other components; conceivably we could have a shared piece of infrastructure, e.g. database or queue.
   I still don't want it deployed to production environments.
3. I want it to go live.

### ModifyService: Modifying an existing service

As a developer I am modifying an existing service.

1. I want to test changes in isolation.
2. I want to test changes with other services.
3. I want to bless a new version and deploy it to production.

### NewSystem: Starting from scratch

I am setting up pib for the very first time.
There are no services, no system.
