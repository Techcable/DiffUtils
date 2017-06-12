DiffUtils
=========
A python diff/patch library supporting unified diffs and with a native diff implementation

## Features
- Myers diff algorithm
  - Same diff algorithm used by git and the unix diff command
- Native diff implementation
  - Native implementation is 10 times faster than the pure-python version
  - A native patch implementation is unneeded since the patch operation is already very fast
  - Precompiled wheels available
- Supports parsing/outputting unified diffs
- Command line interface included
  - Supports recursively diffing/patching entire directory trees

## Credits
- Dmitry Naumenko (dm.naumenko@gmail.com) - Java Version
- [Techcable](https://github.com/Techcable/) - Python Port
