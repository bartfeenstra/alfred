"""Integrates Alfred with Python's setuptools."""

import os

from setuptools import setup, find_packages

ROOT_PATH = os.path.dirname(os.path.abspath(__file__))

with open('/'.join((ROOT_PATH, 'VERSION'))) as f:
    VERSION = f.read()

with open('/'.join((ROOT_PATH, 'requirements.txt'))) as f:
    DEPENDENCIES = f.read().split('\n')

with open('/'.join((ROOT_PATH, 'README.md'))) as f:
    long_description = f.read()

try:
    from m2r import convert

    long_description = convert(long_description)
except ImportError:
    # Allow this to fail, because we cannot guarantee this dependency is installed.
    pass

SETUP = {
    'name': 'alfred',
    'description': 'Your friendly home automator.',
    'long_description': long_description,
    'version': VERSION,
    'license': 'MIT',
    'author': 'Bart Feenstra',
    'url': 'https://github.com/bartfeenstra/alfred',
    'install_requires': DEPENDENCIES,
    'packages': find_packages(),
    'data_files': [
        ('', [
            'LICENSE',
            'README.md',
            'requirements.txt',
            'VERSION',
        ])
    ],
}

if __name__ == '__main__':
    setup(**SETUP)
