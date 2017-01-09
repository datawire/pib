import shlex
import shutil

from .process import quiet_call
from subprocess import call


def is_existent_cluster(name):
    cmd = 'kops get cluster {}'.format(name)
    return quiet_call(cmd) == 0


def delete_cluster(name):
    """Totally and completely delete a cluster"""

    cmd = shlex.split('terraform destroy -force')
    res = call(cmd, cwd='out/{0}/terraform'.format(name))
    if res == 0:
        shutil.rmtree('clusters/{0}/terraform'.format(name))
    else:
        return

    cmd = 'kops delete cluster {0} --yes'.format(name)
    res = call(shlex.split(cmd))
    if res != 0:
        return
