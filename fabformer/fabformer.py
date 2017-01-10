import json
import os

from .util import merge_dicts
from os.path import expanduser
from pathlib import Path

fabformer_home = Path(expanduser('~'), '.fabformer')
fabformer_deps = fabformer_home / 'bin'


class Generator:

    def __init__(self, domain, specs):
        self.domain = domain
        self.specs = dict(specs)
        self.workspace = Path(os.getcwd())

    def load_terraform_vars(self):
        return self.load_json('terraform.tfvars.json')

    def load_terraform_template(self):
        return self.load_json('main.tf.json')

    def load_json(self, workspace_file):
        res = {}
        if (self.workspace / workspace_file).exists():
            with (self.workspace / workspace_file).open('r') as f:
                res = json.load(f)

        return res

    def write_json(self, data, workspace_file):
        with (self.workspace / workspace_file).open('w+') as f:
            json.dump(data, f, indent=4, separators=(',', ': '))

    def generate(self):
        tf_template = self.load_terraform_template()
        tf_vars = self.load_terraform_vars()

        tf_vars['fabric_region'] = 'us-east-1'
        tf_vars['fabric_domain'] = self.domain

        tf_mods = tf_template.get('modules', {})

        # TODO: always generated, needs to be protected from being overridden
        tf_mods['basic'] = {'source': 'github.com/datawire/fabric-modules//basic', 'domain': '${var.fabric_domain}'}

        for name in self.specs:
            print("Generating module {}".format(name))
            (module, outputs) = self.generate_standalone(name)
            tf_mods[name] = module

        tf_template['variable'] = {x: {} for x in tf_vars}
        tf_template['module'] = tf_mods
        tf_template['output'] = {}

        self.write_json(tf_vars, 'terraform.tfvars.json')
        self.write_json(tf_template, 'main.tf.json')

    def generate_standalone(self, name):
        spec = self.specs.get(name)
        (source_type, source_ref) = str(spec.get('source')).split(':')

        module = {}
        output = {}
        link = {}
        if source_type == 'template':
            module = {'source': 'github.com/' + source_ref}
            module = merge_dicts(module, spec.get('config'))

        if source_type == 'generate':
            # TODO: lookup a generator and then feed the spec to the generator.
            pass

        return module, output
