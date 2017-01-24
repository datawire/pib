import boto3
import botocore.exceptions
import json
import os
import shlex
import subprocess


def get_aws_acct_id():
    return boto3.client('sts').get_caller_identity().get('Account')


def get_env():
    branch = os.getenv('TRAVIS_BRANCH', '').lower()
    if branch.startswith('env/'):
        return branch.split('/')[1]
    else:
        raise ValueError('Not an environment branch. Expected format env/$name but found {0}'.format(branch))


class Terraform:

    def __init__(self, name, state_bucket):
        self.name = str(name).lower()
        self.state = S3State(state_bucket, '{}.tfstate'.format(self.name))

    def setup(self):
        """Performs general Terraform setup for before running such as initializing remote state and pulling required
        modules"""

        Terraform.exec(shlex.split("remote config -backend=s3 -backend-config='bucket={0}' -backend-config='key={1}'".format(self.state.bucket, self.state.key)))
        Terraform.exec(shlex.split('get terraform/'))

    # def plan(self):
    #     """Generate a Terraform execution plan for the current state."""
    #     Terraform.exec('plan -out )

    @staticmethod
    def exec(args):
        from subprocess import Popen, PIPE, CalledProcessError
        cmd = ['terraform'] + args
        with Popen(cmd, stdout=PIPE, bufsize=1, universal_newlines=True) as p:
            for line in p.stdout:
                print(line, end='')

        if p.returncode != 0:
            raise CalledProcessError(p.returncode, p.args)

        return p.returncode


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
