"""Remote deployment."""

import json

from .kubectl import Kubectl
from .kubernetes import envfile_to_k8s, RenderingOptions
from .subprocesses import Runner
from .tfstatereader import S3State, extract


class RunRemote(object):
    """Context for running local operations.

    We use kubectl from $PATH, rather than one in ~/.pib.
    """

    def __init__(self, logfile, echo):
        """
        :param logfile: file-like object to write logs to.
        :param echo: callable to write user output to. Presumed to add
            linebreaks.
        """
        self._runner = Runner(logfile)
        self._echo = echo

    def deploy(self, envfile):
        """Deploy current configuration to a remote server."""
        # TODO: missing ability to remove previous iteration of k8s objects!

        # Use the remote address as context for kubectl:
        kubectl = Kubectl(self._runner, ["kubectl"], envfile.remote.address)

        state_path = envfile.remote.state
        file_prefix = "terraform:file://"
        s3_prefix = "terraform:s3://"
        if state_path.startswith(file_prefix):
            with open(state_path[:len(file_prefix)]) as f:
                data = json.load(f)
        elif state_path.startswith(s3_prefix):
            bucket, key = state_path[:len(s3_prefix)].split("/", 1)
            data = S3State(bucket, key).fetch()
        extracted_state = extract(data)

        # Assume only one application:
        app_state = next(extracted_state.applications)
        options = RenderingOptions(tag_overrides={},
                                   # Make services private:
                                   private_service_type="ClusterIP")
        for k8s_config in envfile_to_k8s(envfile, app_state):
            kubectl.apply_config(k8s_config.render(options))
