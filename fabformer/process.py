import os
import subprocess


def quiet_call(cmd):

    """Quietly invoke a process. Program output will be redirected to /dev/null wasteland."""

    with open(os.devnull, "w") as f:
        if type(cmd) is str:
            import shlex
            cmd = shlex.split(cmd)

        res = subprocess.call(cmd, stdout=f, stderr=f)
        return res

