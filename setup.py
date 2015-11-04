#!/usr/bin/env python

from distutils.core import setup

setup(name='DiffUtils',
      version='1.0.3-SNAPSHOT',
      description='A python diff/patch library based on java-diff-utils (https://code.google.com/p/java-diff-utils/)',
      author='Techcable',
      author_emails='Techcable@outlook.com',
      packages=['diffutils'],
      requires=["enum34"]
      )
