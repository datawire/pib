"""Convert terraform state into Kuberentes configuration."""

import boto3
import botocore
import json

from .kubernetes import ExternalRequiresConfigMap


class Metadata:
    """Metadata for a particular resource, e.g. AWS RDS instance."""

    def __init__(self, app, service, component_name):
        self.app = app
        self.service = service
        self.component_name = component_name


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


class Injectable:
    """An object that can be injected as configuration into Kubernetes."""
    def __init__(self, resource_type, app, service, resource_name, config):
        self.resource_type = resource_type  # Mainly useful for debugging
        self.app = app  # application name
        self.service = service  # service name, or None if shared resource
        self.resource_name = resource_name  # name of resource
        self.config = config  # the configuration to put into k8s ConfigMap

    def render(self):
        name = self.resource_name
        if self.service is not None:
            name = self.service + "---" + name
        return ExternalRequiresConfigMap(
            name=name, resource_name=self.resource_name, data=self.config)


def create_aws_elasticsearch_domain(tf_data):
    return {'HOST': tf_data['attributes']['endpoint'],
            'PORT': "80"}  # doesn't have one...


def create_aws_database_resource(tf_data):
    return {'HOST': tf_data['attributes']['address'],
            'PORT': tf_data['attributes']['port'],
            'USERNAME': tf_data['attributes']['username'],
            'PASSWORD': tf_data['attributes']['password']}


class ExtractedState:
    """Injectables extracted from terraform state."""
    def __init__(self):
        self.all = []
        self.app_resources = {}  # map app name to Injectable
        self.svc_resources = {}  # map service name to Injectable

    def add_resource(self, resource):
        self.all.append(resource)
        self.app_resources.setdefault(resource.app, []).append(resource)

        # resource.service can be None which means it's shared and therefore
        # doesn't belong to any particular resource.
        if resource.service is not None:
            self.svc_resources.setdefault(resource.service, []).append(
                resource)

    def clear(self):
        self.all.clear()
        self.app_resources.clear()
        self.svc_resources.clear()

    def size(self):
        return len(self.all)

    def render(self, renderer):
        renderer.render(self)


RESOURCE_FACTORIES = {
    'aws_db_instance': create_aws_database_resource,
    'aws_rds_cluster': create_aws_database_resource,
    'aws_elasticsearch_domain': create_aws_elasticsearch_domain,
}


def extract(raw_json):
    """Convert terraform JSON state into an ExtractedState object."""
    tfstate = json.loads(raw_json)
    extracted = ExtractedState()

    for mod in tfstate['modules']:
        extract_resources_from_module(extracted, mod)

    return extracted


def extract_resources_from_module(result, mod):
    """Extract resources from a terraform state module."""
    # module.resources is a dictionary that maps the Terraform templates
    # resource name to data about that resource. We are not interested in that
    # value. The interesting info lies in the tf_data dictionary.
    for tf_name, tf_data in mod.get('resources', {}).items():

        # there's a huge number of Terraform resources we can't do anything
        # intelligent with.
        if tf_data['type'] not in RESOURCE_FACTORIES:
            print("SKIP: no type handler for type {}".format(tf_data['type']))
            continue

        # TODO(plombardi): INVESTIGATE
        # there's a 'primary' and a 'deposed'... I'm not sure what deposed is
        # or if it's relevant to anything. Primary data is the stuff we're
        # after.
        primary = tf_data['primary']

        # tainted stuff is going to be destroyed by Terraform so do not do
        # anything with it.
        if primary['tainted']:
            print("SKIP: tainted resource")
            continue

        attributes = primary['attributes']
        tags = extract_tags(attributes)

        # The metadata holds app and service name information. We use a JSON
        # object to store that information to avoid wasting AWS resource tags
        # because each resource can only have a maximum of 10. If a resource
        # does not have metadata it's not meant to be consumed.
        raw_metadata = json.loads(tags.get('pib_metadata', '{}'))
        if not raw_metadata:
            print("SKIP: no metadata")
            continue

        result.add_resource(
            Injectable(tf_data['type'],
                       raw_metadata.get('app', 'default'),
                       raw_metadata.get('service'),
                       raw_metadata['component_name'],
                       RESOURCE_FACTORIES[tf_data['type']](primary)))


def extract_tags(attributes):
    result = {}
    for k, v in attributes.items():
        # TODO: no idea why they seem to use .# and .% at different types or if
        # means something...
        if k.startswith('tags.') and k not in {'tags.#', 'tags.%'}:
            result[k.split('.', 1)[-1]] = v

    return result
