DiffUtils ![pypi version](https://img.shields.io/pypi/v/diffutils.svg) ![supported versions](https://img.shields.io/pypi/pyversions/diffutils.svg) ![wheel](https://img.shields.io/pypi/wheel/Django.svg) [![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://black.readthedocs.io/en/stable/) [![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)
=========
A python diff/patch library supporting unified diffs and native acceleration.

## Features
- Myers diff algorithm
  - Same diff algorithm used by git and the unix diff command
- Native diff implementation
  - Native implementation is 10 times faster than the pure-python version
  - A native patch implementation is unneeded since the patch operation is already very fast
  - Precompiled wheels available for Linux on officially supported python versions
    - Some wheels are made available for Windows and Mac, but there are no guarantees.
- Highly descriptive error messages
- Supports parsing/outputting unified diffs
- Command line interface included
  - Supports recursively diffing/patching entire directory trees


## Credits
- Dmitry Naumenko (dm.naumenko@gmail.com) - Java Version
- [Techcable](https://github.com/Techcable/) - Python Port
