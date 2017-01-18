import os
import requests
import yaml


class Environment:

    def __init__(self, name, raw):
        self.name = str(name)
        self.raw = raw or {}

    def components(self):
        return set(self.raw.get('components', []))

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        return NotImplemented

    def __ne__(self, other):
        if isinstance(other, self.__class__):
            return not self.__eq__(other)
        return NotImplemented


class Stack:

    def __init__(self, raw):
        self.raw = raw or {}

    def requirements(self):
        return set(self.raw.get('requires', []))

    def name(self):
        return self.raw.get('name')

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        return NotImplemented

    def __ne__(self, other):
        if isinstance(other, self.__class__):
            return not self.__eq__(other)
        return NotImplemented


def fetch_remote_yaml(url):
    # allows us to hit private repositories
    credentials = os.getenv('GITHUB_CREDENTIALS', None)
    credentials = credentials.split(':') if credentials else ()

    resp = requests.get(url, auth=credentials)
    return yaml.load(resp.text)


def load_envfile():
    with open('Envfile.yaml', 'r') as f:
        return yaml.load(f)


def fetch_envfile(url):
    return fetch_remote_yaml(url)


def fetch_pibstack(url):
    return fetch_remote_yaml(url)


def filter_environments(envfile):
    # The name 'local' is a special environment that is presumed to be on a developer's workstation. All other
    # environments should be filtered out if they do not specify 'auto_deploy: True'.
    environments = envfile.get('environments', {})
    environments.pop('local', None)

    res = {}
    for name, data in environments.items():
        if data.get('auto_deploy', False):
            res[name] = Environment(name, data)

    return res


def create_stack(docker_tag, fetched):
    data = dict(fetched)
    docker_repo = data.get('image').get('repo')
    fetched['image']['repo'] = "{}:{}".format(docker_repo, docker_tag)
    return Stack(fetched)


def deploy(envfile):
    environments = filter_environments(envfile)
    if not environments:
        print('No environments are not defined')
        return

    stacks = []
    for (k, v) in envfile.get('applications', {}).items():
        fetched = fetch_pibstack(v.get('descriptor'))
        stack = create_stack(v.get('docker_tag'), fetched)
        stacks.append(stack)

    if not stacks:
        print('No applications are defined.')
        return

    # check that stuff is insane for all environments before attempting to apply it to anyone.
    for env in environments:
        for stack in stacks:
            if not sanity(env, stack):
                return

    # sanity checked out
    for env in environments:
        apply_env(env, stacks)


def sanity(env, stack):
    """Perform some basic sanity checks, for example, ensure requirements specified in the stack can be satisfied"""
    for required in stack.requirements():
        if required not in env.components():
            print("Requirement '{0}' for '{1}' not defined in environment '{2}'".format(required,
                                                                                        stack.name(),
                                                                                        env.name))
            return False

    return True


def apply_env(env, stacks):
    print('Apply updates to environment {}'.format(env))
    for stack in stacks:
        pass








