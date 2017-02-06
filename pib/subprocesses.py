"""Infrastructure for running subprocesses."""

from subprocess import check_call, check_output


class Runner(object):
    """Context for running subprocesses."""

    def __init__(self, logfile):
        """
        :param logfile: file-like object to write logs to.
        """
        self.logfile = logfile

    def check_call(self, *args, **kwargs):
        """Run a subprocess, make sure it exited with 0."""
        self.logfile.write("Running: {}\n".format(args))
        self.logfile.flush()
        check_call(*args, stdout=self.logfile, stderr=self.logfile, **kwargs)

    def get_output(self, *args, **kwargs):
        """Return (stripped) command result as unicode string."""
        self.logfile.write("Running: {}\n".format(args))
        self.logfile.flush()
        return str(check_output(*args, stderr=self.logfile, **kwargs).strip(),
                   "utf-8")
