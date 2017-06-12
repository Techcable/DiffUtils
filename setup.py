#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name='DiffUtils',
    version='1.0.4.dev0',
    description='A python diff/patch library based on java-diff-utils (https://code.google.com/p/java-diff-utils/)',
    author='Techcable',
    author_email='Techcable@outlook.com',
    packages=find_packages(include="diffutils*"),
    requires=["argh"],
    setup_requires=["pytest-runner"],
    tests_require=["pytest"]
)
