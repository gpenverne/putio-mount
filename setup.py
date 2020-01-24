#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name="PutioMount",
    version="2",
    description="Mount put.io as a local drive",
    author="Gregoire Penverne",
    keywords="put.io mount fuse",
    packages=find_packages(),
    license="MIT",
    url="https://github.com/gpenverne/putio-mount",
    install_requires=["putio.py", "fusepy", "requests", "inotify", "urllib3"],
)
