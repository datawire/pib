from setuptools import setup, find_packages

import versioneer


setup(
    name='pib',
    description='Pib: dev and prod application stacks on Kubernetes',
    packages=find_packages(exclude=['tests']),
    entry_points={
        'console_scripts': [
            'pib=pib.cli:cli',
            'fabformer=fabformer.cli:cli'
        ],
    },
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
)
