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
    def __init__(self, metadata, config):
        self.config = config
        self.metadata = metadata

    def render(self):
        return ExternalRequiresConfigMap(
            name=self.metadata.service,
            resource_name=self.metadata.component_name,
            data=self.config)


class AwsElasticsearchDomain(Injectable):

    def __init__(self, metadata, config):
        Injectable.__init__(self, metadata, config)

    @staticmethod
    def create(pib_metadata, tf_data):
        config = {'HOST': tf_data['attributes']['endpoint'],
                  'PORT': "80"}  # doesn't have one...

        return AwsElasticsearchDomain(pib_metadata, config)


class AwsDatabaseResource(Injectable):

    def __init__(self, metadata, config):
        Injectable.__init__(self, metadata, config)

    @staticmethod
    def create(pib_metadata, tf_data):
        config = {'HOST': tf_data['attributes']['address'],
                  'PORT': tf_data['attributes']['port'],
                  'USERNAME': tf_data['attributes']['username'],
                  'PASSWORD': tf_data['attributes']['password']}

        return AwsDatabaseResource(pib_metadata, config)


class ExtractedState:
    """Injectables extracted from terraform state."""
    def __init__(self):
        self.all = []
        self.app_resources = {}  # map app name to Injectable
        self.svc_resources = {}  # map service name to Injectable

    def add_resource(self, resource):
        self.all.append(resource)
        self.app_resources.setdefault(
            resource.metadata.app, []).append(resource)

        # resource.service can be None which means it's shared and therefore
        # doesn't belong to any particular resource.
        if resource.metadata.service is not None:
            self.svc_resources.setdefault(
                resource.metadata.service, []).append(resource)

    def clear(self):
        self.all.clear()
        self.app_resources.clear()
        self.svc_resources.clear()

    def size(self):
        return len(self.all)

    def render(self, renderer):
        renderer.render(self)


RESOURCE_FACTORIES = {
    'aws_db_instance': AwsDatabaseResource.create,
    'aws_rds_cluster': AwsDatabaseResource.create,
    'aws_elasticsearch_domain': AwsElasticsearchDomain.create
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
        # there's a 'primary' and a 'deposed'... I'm not sure what deposed is or if it's relevant to anything. Primary
        # data is the stuff we're after.
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

        metadata = Metadata(raw_metadata['app'],
                            raw_metadata.get('service'),
                            raw_metadata['component_name'])

        injectable = RESOURCE_FACTORIES[tf_data['type']](metadata, primary)
        result.add_resource(injectable)


def extract_tags(attributes):
    result = {}
    for k, v in attributes.items():
        # TODO: no idea why they seem to use .# and .% at different types or if
        # means something...
        if k.startswith('tags.') and k not in {'tags.#', 'tags.%'}:
            result[k.split('.', 1)[-1]] = v

    return result
