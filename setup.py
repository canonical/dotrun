#! /usr/bin/env python3

# Core
import sys
from setuptools import setup

# The importer relies heavily on glob recursive search capability.
# This was only introduced in Python 3.5:
# https://docs.python.org/3.6/whatsnew/3.5.html#glob
assert sys.version_info >= (3, 5), (
    "dotrun requires Python 3.5 or newer"
)

setup(
    name='canonicalwebteam.dotrun',
    version='0.1.0',
    author='Canonical webteam',
    author_email='robin+pypi@canonical.com',
    url='https://github.com/canonical-web-and-design/dotrun',
    packages=[
        'canonicalwebteam.dotrun',
    ],
    description=(
        'A command-line tool for running projects.'
    ),
    long_description=open('README.rst').read(),
    install_requires=[
        'ipdb',
        'poetry',
        'virtualenv'
    ],
    scripts=['dotrun']
)
