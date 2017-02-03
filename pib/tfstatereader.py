"""Convert terraform state into Kuberentes configuration."""

import json

import boto3
import botocore
from pyrsistent import PClass, pmap_field, pset_field, field, PSet, freeze

from .kubernetes import ExternalRequiresConfigMap


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


class Injectable(PClass):
    """An object that can be injected as configuration into Kubernetes."""
    resource_type = field(str)  # Mainly useful for debugging
    app = field(str)  # application name
    # service name, or None if shared resource:
    service = field((str, type(None)))
    resource_name = field(str)  # name of resource
    # the configuration to put into k8s ConfigMap:
    config = pmap_field(str, str)

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


class ApplicationState(PClass):
    """Per-application injectable state."""
    shared_resources = pset_field(Injectable)
    # map service name -> set of Injectables
    service_resources = pmap_field(str, PSet)


class ExtractedState(PClass):
    """Injectables extracted from terraform state."""
    # map application name to its state:
    applications = pmap_field(str, ApplicationState)

    def size(self):
        # TODO: delete me
        return sum(len(app.shared_resources) +
                   sum(map(len, app.service_resources.values()))
                   for app in self.applications.values())


RESOURCE_FACTORIES = {
    'aws_db_instance': create_aws_database_resource,
    'aws_rds_cluster': create_aws_database_resource,
    'aws_elasticsearch_domain': create_aws_elasticsearch_domain,
}


def extract(raw_json):
    """Convert terraform JSON state into an ExtractedState object."""
    tfstate = json.loads(raw_json)
    result = {}

    for mod in tfstate['modules']:
        for injectable in extract_resources_from_module(mod):
            app_state = result.setdefault(injectable.app,
                                          {"shared_resources": set(),
                                           "service_resources": {}})
            if injectable.service is None:
                app_state["shared_resources"].add(injectable)
            else:
                app_state["service_resources"].setdefault(
                    injectable.service, set()).add(injectable)

    return ExtractedState.create(freeze({"applications": result}))


def extract_resources_from_module(mod):
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

        yield Injectable(resource_type=tf_data['type'],
                         app=raw_metadata.get('app', 'default'),
                         service=raw_metadata.get('service'),
                         resource_name=raw_metadata['resource_name'],
                         config=RESOURCE_FACTORIES[tf_data['type']](primary))


def extract_tags(attributes):
    result = {}
    for k, v in attributes.items():
        # TODO: no idea why they seem to use .# and .% at different types or if
        # means something...
        if k.startswith('tags.') and k not in {'tags.#', 'tags.%'}:
            result[k.split('.', 1)[-1]] = v

    return result
