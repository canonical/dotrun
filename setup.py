#! /usr/bin/env python3

# Core
import sys
from setuptools import setup

# The importer relies heavily on glob recursive search capability.
# This was only introduced in Python 3.5:
# https://docs.python.org/3.6/whatsnew/3.5.html#glob
assert sys.version_info >= (3, 5), "dotrun requires Python 3.5 or newer"

setup(
    name="canonicalwebteam.dotrun",
    version="0.0.0",
    packages=["canonicalwebteam.dotrun"],
    install_requires=["ipdb", "termcolor", "virtualenv", "python-dotenv"],
    entry_points={"console_scripts": ["dotrun = canonicalwebteam.dotrun:cli"]},
)
