"""Code for interacting with Kubernetes cluster using kubectl."""

from tempfile import NamedTemporaryFile

from yaml import safe_dump


class Kubectl(object):
    """kubectl wrapper."""

    def __init__(self, runner, path, context):
        """
        :param runner Runner: The runner to use to run ``kubectl``.
        :param path Path: The path to the kubectl binary.
        :param context str: The k8s context, e.g. "minikube".
        """
        self._runner = runner
        self._path = path
        self._context = context

    def run(self, args):
        """Run kubectl.

        :param args: The kubectl command-line arguments.
        """
        self._runner.check_call(
            [str(self._path), "--context={}".format(self._context)] + args)

    def apply_config(self, config):
        """Run 'kubectl apply' on the given config."""
        # TODO: not deleting these is a security risk, but useful for
        # debugging. switch to just piping into kubectl stdin in future.
        with NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
            f.write(safe_dump(config))
            f.flush()
            self.run(["apply", "-f", f.name])
