
# NOTE: Must be first import to check version
import diffutils
import argh
from argh import arg, CommandError
from pathlib import Path
import os
from diffutils.output import generate_unified_diff
from diffutils.engine import DiffEngine
from diffutils.api import parse_unified_diff, PatchFailedException


def do_diff(engine: DiffEngine, original: Path, revised: Path, output: Path, context_size=5, force=False):
    original_lines = []
    revised_lines = []
    with open(original, 'rt') as f:
        for line in f:
            original_lines.append(line.rstrip("\r\n"))
    with open(revised, 'rt') as f:
        for line in f:
            revised_lines.append(line.rstrip("\r\n"))
    result = engine.diff(original_lines, revised_lines)
    if not original.is_absolute():
        original_name = str(original)
    else:
        original_name = str(original.relative_to(Path.cwd()))
    if not revised.is_absolute():
        revised_name = str(revised)
    else:
        revised_name = str(revised.relative_to(Path.cwd()))
    try:
        result_lines = []
        empty = True
        for line in generate_unified_diff(
            original_name,
            revised_name,
            original_lines,
            result,
            context_size=context_size
        ):
            if empty and line.strip():
                empty = False
            result_lines.append(line)
        if empty:
            return False
        with open(output, 'wt' if force else 'xt') as f:
            for line in result_lines:
                f.write(line)
                f.write('\n')
        return True
    except FileExistsError:
        raise CommandError(f"Output file already exists: {output}")


def do_patch(patch_file: Path, original: Path, output: Path, context_size=5, force=False):
    original_lines = []
    patch_lines = []
    with open(patch_file, 'rt') as f:
        for line in f:
            patch_lines.append(line.rstrip("\r\n"))
    patch = parse_unified_diff(patch_lines)
    patch_lines = None  # Free
    with open(original, 'rt') as f:
        for line in f:
            original_lines.append(line.rstrip("\r\n"))
    try:
        result_lines = patch.apply_to(original_lines)
    except PatchFailedException as e:
        raise CommandError(str(e)) from None
    try:
        with open(output, 'wt' if force else 'xt') as f:
            for line in result_lines:
                f.write(line)
                f.write('\n')
    except FileExistsError:
        raise CommandError(f"Output file already exists: {output}")


@arg('original', type=Path, help="The original file/directory")
@arg('revised', type=Path, help="The revised file/directory")
@arg('output', type=Path, help="The output file/directory")
@arg('--ignore-missing', '-i', help="Ignore revised files that are missing from the original dir")
@arg('--implementation', '--impl', help="Specify the diff implementation to use")
@arg('--context', '-c', help="Specify the number of lines of context to output in the patch")
@arg('--unrestricted', '-u', help="Search hidden files and directories")
@arg('--force', '-f', help="Forcibly override existing patches")
def diff(original: Path, revised: Path, output: Path, ignore_missing=False, implementation=None, context=5, unrestricted=False, force=False):
    """Compute the difference between the original and revised text"""
    if not original.exists():
        raise CommandError(f"Original file doesn't exist: {original}")
    if not revised.exists():
        raise CommandError(f"Revised file doesn't exist: {revised}")
    try:
        engine = DiffEngine.create(name=implementation)
    except ImportError as e:
        raise CommandError("Unable to import {} implementation!") from e
    if original.is_dir():
        if not revised.is_dir():
            raise CommandError(f"Original {original} is a directory, but revised {revised} is a file!")
        for revised_root, dirs, files in os.walk(str(revised)):
            for revised_file_name in files:
                if not unrestricted and revised_file_name.startswith('.'):
                    continue
                revised_file = Path(revised_root, revised_file_name)
                relative_path = revised_file.relative_to(revised)
                original_file = Path(original, relative_path)
                if not original_file.exists():
                    if ignore_missing:
                        continue
                    else:
                        raise CommandError(f"Revised file {revised_file} doesn't have matching original {original_file}!")
                output_file = Path(output, relative_path.parent, relative_path.name + ".patch")
                output_file.parent.mkdir(parents=True, exist_ok=True)
                if do_diff(engine, original_file, revised_file, output_file, context_size=context, force=force):
                    print(f"Computed diff: {relative_path}")
            if not unrestricted:
                hidden_dirs = [d for d in dirs if d.startswith('.')]
                for d in hidden_dirs:
                    dirs.remove(d)
    else:
        if not revised.is_file():
            raise CommandError(f"Original {original} is a file, but revised {revised} is a directory!")
        do_diff(engine, original, revised, output, context_size=context, force=force)


@arg('patches', type=Path, help="The patches to apply")
@arg('original', type=Path, help="The original file/directory")
@arg('output', type=Path, help="Where to output the revised files")
@arg('--force', '-f', help="Forcibly override existing files")
def patch(patches: Path, original: Path, output: Path, force=False):
    """Applies the specified patches to the original files, producing the revised text"""
    if not patches.exists():
        raise CommandError(f"Patch file doesn't exist: {patches}")
    if not original.exists():
        raise CommandError(f"Original file doesn't exist: {original}")
    if patches.is_dir():
        if not original.is_dir():
            raise CommandError(f"Patches {patches} is a directory, but original {original} is a file!")
        for patch_root, dirs, files in os.walk(str(patches)):
            for patch_file_name in files:
                patch_file = Path(patch_root, patch_file_name)
                if patch_file.suffix != '.patch':
                    raise CommandError(f"Patch file doesn't end with '.patch': {patch_file_name}")
                relative_path = Path(patch_file.parent.relative_to(patches), patch_file.stem)
                original_file = Path(original, relative_path)
                output_file = Path(output, relative_path)
                if not original_file.exists():
                    raise CommandError(f"Couldn't find  original {original_file} for patch {patch_file}!")
                output_file.parent.mkdir(parents=True, exist_ok=True)
                do_patch(patch_file, original_file, output_file, force=force)
    else:
        if not original.is_file():
            raise CommandError(f"Patches {patches} is a file, but origianl {original} is a directory!")
        do_patch(patches, original, output, force=force)


@arg('patch_file', type=Path, help="The patch file to fix")
@arg('original_file', type=Path, help="The original file, used to output context information")
@arg('--strict', help="Strictly parse the patch, failing on any errors")
@arg('--context', '-c', help="Specify the context to use when re-emitting the patch")
def fix_patch(patch_file: Path, original_file: Path, strict=False, context=5):
    """Fixes errors detected in the patch, by leniently parsing it and then re-emitting it"""
    if not patch_file.is_file():
        if patch_file.exists():
            raise CommandError(f"Patch file is a directory: {patch_file}")
        else:
            raise CommandError(f"Patch file doesn't exist: {patch_file}")
    if not original_file.is_file():
        if original_file.exists():
            raise CommandError(f"Original file is a directory: {original_file}")
        else:
            raise CommandError(f"Original file doesn't exist: {original_file}")
    patch_lines = []
    # TODO: Make a public API for parsing original_name and revised_name
    original_name, revised_name = None, None
    with open(patch_file, 'rt') as f:
        for line in f:
            if original_name is None and line.startswith('---'):
                original_name = line[3:].split()[0]
            elif revised_name is None and line.startswith('+++'):
                revised_name = line[3:].split()[0]
            patch_lines.append(line.rstrip("\r\n"))
    original_lines = []
    with open(original_file, 'rt') as f:
        for line in f:
            original_lines.append(line.rstrip("\r\n"))
    if original_name is None:
        raise CommandError(f"Unable to detect original file name in {patch_file}")
    elif revised_name is None:
        raise CommandError(f"Unable to detect revised file name in {patch_file}")
    patch = parse_unified_diff(patch_lines, lenient=not strict)
    with open(patch_file, 'wt') as f:
        for line in generate_unified_diff(
            original_name,
            revised_name,
            original_lines,
            patch,
            context_size=context
        ):
            f.write(line)
            f.write('\n')


def main():
    parser = argh.ArghParser(description="A diff/patch utility")
    parser.add_commands([diff, patch, fix_patch])
    parser.dispatch()


if __name__ == "__main__":
    main()
