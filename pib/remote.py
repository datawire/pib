import boto3
import botocore.exceptions
import json
import os
import shlex
from pathlib import Path
from subprocess import Popen, PIPE, CalledProcessError


def get_aws_acct_id():
    return boto3.client('sts').get_caller_identity().get('Account')


def get_env():
    branch = os.getenv('TRAVIS_BRANCH', '').lower()
    if branch.startswith('env/'):
        return branch.split('/')[1]
    else:
        raise ValueError('Not an environment branch. Expected format env/$name but found {0}'.format(branch))


def merge_dicts(defaults, overrides):
    res = {}
    res.update(defaults)
    res.update(overrides)
    return res


def run(cmd, allowed_exit_codes={0}, **kwargs):
    if type(cmd) is str:
        cmd = shlex.split(cmd)

    merged = merge_dicts({'stdout': PIPE, 'bufsize': 1, 'universal_newlines': True}, {})
    with Popen(cmd, **merged) as proc:
        for line in proc.stdout:
            print(line, end='')

    status = proc.returncode
    if status not in allowed_exit_codes:
        raise CalledProcessError(status, cmd, None)

    return proc.returncode


class RemoteDeploy:

    def __init__(self, config):
        self.config = config
        self.prepared = False

    def prepare(self):
        """Perform preparations before performing any type of remote operations, for example, fetching remote Terraform
        state or downloading required modules."""
        state_bucket = self.config.get('state_bucket')
        environment = self.config.get('environment')
        be_config = "-backend-config='bucket={0}' -backend-config='key={1}.tfstate'".format(state_bucket, environment)
        run("terraform remote config -backend=s3 {}".format(be_config))
        run("terraform get terraform/")
        self.prepared = True

    def generate_tfvars(self):
        """Generate Terraform variables that are automatically inferred from the execution of pib remote, for example,
        the environment name."""
        return {'environment': self.config.get('environment')}

    def plan(self):
        tfvars_file = Path('terraform/terraform.tfvars.json')
        tfvars = {}
        if tfvars_file.exists():
            with tfvars_file.open('r') as f:
                tfvars = json.load(f)

        tfvars = merge_dicts(tfvars, self.generate_tfvars())

        with tfvars_file.open('w+') as f:
            json.dump(tfvars, f)

        res = run('terraform plan -var-file=terraform/terraform.tfvars.json -out terraform/plan.out --detailed-exitcode terraform/', allowed_exit_codes={0, 1, 2})

    def apply(self):
        run('terraform apply -var-file=terraform/terraform.tfvars.json terraform/plan.out')

    def inject(self):
        """Inject Terraform information into Kubernetes"""
        pass


class S3State:
    """Operations pertaining to the specified S3 state storage facilities."""

    def __init__(self, bucket, key):
        self.bucket = str(bucket)
        self.key = key

    def exists(self):
        return self.__bucket_exists() and self.__key_exists()

    def fetch(self):
        s3 = boto3.client('s3')
        obj = s3.get_object(Bucket=self.bucket, Key=self.key)
        content = obj['Body'].read().decode('utf-8')
        return json.loads(content)

    def __bucket_exists(self):
        res = True
        s3 = boto3.client('s3')

        try:
            s3.head_bucket(Bucket=self.bucket)
        except botocore.exceptions.ClientError as e:
            res = False

        return res

    def __key_exists(self):
        res = True
        s3 = boto3.client('s3')

        try:
            s3.head_object(Bucket=self.bucket, Key=self.key)
        except botocore.exceptions.ClientError as e:
            res = False

        return res
