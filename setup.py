#!/usr/bin/env python

from setuptools import setup

setup(name='PutioMount',
      version='1.0',
      description='Mount put.io as a local drive',
      author='Gregoire Penverne',
      license='MIT',
      url='https://github.com/gpenverne/putio-mount',
      install_requires=['putio.py', 'fusepy', 'requests', 'inotify']
     )
