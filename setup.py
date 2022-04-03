#!/usr/bin/env python

import os
import sys

from Cython.Build import cythonize
from setuptools import find_packages, setup
from setuptools.extension import Extension

debug_str = os.getenv("DEBUG")
if debug_str is None:
    debug = False
else:
    debug = debug_str.lower() not in ("false", "no", "n")
compile_args = ["-Wall"]
if debug:
    # Enable debug optimizations and debug info
    compile_args.extend(("-Og", "-g"))
else:
    opt_level = os.getenv("OPT_LEVEL")
    if opt_level is None:
        # NOTE: -Os, -O2, and -O3 are 200K, 312K, and 320K respectively
        # They benchmark at 64.2, 52.2, and 52.6 ms respectively
        # Therefore, we'll just stick with -O2 as -O3 is a negligable speedup
        opt_level = "3"
    compile_args.append("-O{}".format(opt_level))

hash_impl = os.getenv("HASH_IMPL")
if hash_impl is None:
    if sys.platform == "linux" or "bsd" in sys.platform:
        # Default to openssl on linux and bsd, where it's included by default
        # and kept up to date and secure.
        hash_impl = "openssl"
    else:
        # Fallback to hashlib on all other systems, since openssl either isn't included (windows),
        # or it uses an outdated and insecure version (mac).
        hash_impl = "hashlib"
extra_sources, libraries, compile_time_env = [], [], {}
if hash_impl in ("openssl",):
    compile_time_env["USE_HASHLIB"] = 0
    extra_sources.append("diffutils/_native/hashing/shared_hasher.c")
    if hash_impl == "openssl":
        print("Using accelerated OpenSSL hashing")
        extra_sources.append("diffutils/_native/hashing/openssl_hasher.c")
        libraries.extend(["dl", "crypto"])
    else:
        raise AssertionError(hash_impl)
elif hash_impl == "hashlib":
    print("Using fallback hashlib hashing")
    compile_time_env["USE_HASHLIB"] = 1
else:
    raise AssertionError("Unknown hash impl: {}".format(hash_impl))

setup(
    name="diffutils",
    version="1.0.7",
    description="A python diff/patch library, with support for unified diffs and a native diff implementation",
    author="Techcable",
    author_email="Techcable@outlook.com",
    packages=find_packages(include="diffutils*"),
    requires=["argh"],
    ext_modules=cythonize(
        Extension(
            "diffutils._native.myers",
            sources=["diffutils/_native/myers.pyx", *extra_sources],
            extra_compile_args=compile_args,
            libraries=libraries,
        ),
        compile_time_env=compile_time_env,
        gdb_debug=debug,
    ),
    keywords="diff patch myers",
    license="MIT",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
    ],
    setup_requires=["pytest-runner"],
    tests_require=["pytest"],
)
