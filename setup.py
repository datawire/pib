from setuptools import setup, find_packages

setup(
    name='pib',
    description='Pib: dev and prod application stacks on Kubernetes',
    packages=find_packages(exclude=['tests']),
    entry_points={
        'console_scripts': [
            'pib=pib.cli:main',
        ],
    },
)
