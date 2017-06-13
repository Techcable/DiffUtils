#!/usr/bin/env python

from setuptools import setup, find_packages
from setuptools.extension import Extension
from Cython.Build import cythonize
import os

debug_str = os.getenv('DEBUG')
if debug_str is None:
    debug = False
else:
    debug = debug_str.lower() not in ("false", "no", "n")
compile_args = ["-w"]  # NOTE: -w disables warnings since we can't do anything about them
if debug:
    # Enable debug optimizations and debug info
    compile_args.extend(("-Og", "-g"))
else:
    opt_level = os.getenv("OPT_LEVEL")
    if opt_level is None:
        # NOTE: -Os, -O2, and -O3 are 200K, 312K, and 320K respectively
        # They benchmark at 64.2, 52.2, and 52.6 ms respectively
        # Therefore, we'll just stick with -O2 as -O3 is a negligable speedup
        opt_level = '3'
    compile_args.append(f"-O{opt_level}")

setup(
    name='diffutils',
    version='1.0.5',
    description='A python diff/patch library, with support for unified diffs and a native diff implementation',
    author='Techcable',
    author_email='Techcable@outlook.com',
    packages=find_packages(include="diffutils*"),
    requires=["argh"],
    ext_modules=cythonize(
        Extension(
            "diffutils._native.myers",
            ["diffutils/_native/myers.pyx"],
            extra_compile_args=compile_args
        ),
        gdb_debug=debug
    ),
    setup_requires=["pytest-runner"],
    tests_require=["pytest"]
)
