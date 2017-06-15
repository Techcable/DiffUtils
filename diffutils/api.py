# Copyright 2010 Dmitry Naumenko (dm.naumenko@gmail.com)
# Copyright 2015 Techcable
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import re
from . import output
from diffutils.core import Patch, PatchFailedException, Chunk
from diffutils.engine import DiffEngine
import warnings

__all__ = (
    "diff",
    "patch",
    "undo_patch",
    "PatchFailedException",
    "PatchFormatError",
    "PatchFormatWarning",
    "parse_unified_diff",
    "generate_unified_diff"
)

"""The public API for DiffUtils"""

__unifiedDiffChunkRe = re.compile("^@@\\s+-(?:(\\d+)(?:,(\\d+))?)\\s+\\+(?:(\\d+)(?:,(\\d+))?)\\s+@@$")


def diff(original, revised):
    """
    Computes the difference between the original and revised list of elements with the default diff algorithm.

    :param original: The original text. Can't be None.
    :param revised: The revised text. Can't be None.
    :return: The patch describing the difference between the original and revised text.
    """
    if isinstance(original, str):
        original = original.splitlines()
    if isinstance(revised, str):
        original = original.splitlines()
    patch = DiffEngine.INSTANCE.diff(original, revised)
    if not patch.deltas:
        return None
    return patch


def patch(original, patch):
    """
    Apply the patch to the given text.

    :param original: the original text to patch
    :param patch: the patch to apply
    :exception PatchFailedException: if unable to apply
    :return: the revised text
    """
    if isinstance(original, str):
        original = original.splitlines()
    return patch.apply_to(original)


def undo_patch(revised, patch):
    """
    Undo the changes specified in the given patch

    :param revised: the changed text
    :param patch: the patch to undo the changes in
    :exception PatchFailedException: if unable to undo the changes
    :return: the original text
    """
    if isinstance(revised, str):
        revised = revised.splitlines()
    patch.restore(revised)


class PatchFormatError(Exception):
    def __init__(self, message: str, line_number: int, line: str) -> None:
        self.message = message
        self.line_number = line_number
        self.line = line

    def __str__(self):
        return f"{self.message} on line {self.line_number}"


class PatchFormatWarning(Warning, PatchFormatError):
    def __init__(self, message, line_number, line):
        PatchFormatError.__init__(self, message, line_number, line)
        assert hasattr(self, 'message'), f"Missing message: {dir(self)}"


def parse_unified_diff(text, lenient=False):
    """
    Parse the given text in unified format into a patch.

    :param text: the unified diff
    :return: the parsed patch
    """
    if isinstance(text, str):
        text = text.splitlines()
    elif not isinstance(text, list):
        text = list(text)

    def report_error(message, line_number, line):
        if lenient:
            warnings.warn(PatchFormatWarning(message, line_number, line))
        else:
            raise PatchFormatError(message, line_number, line)
    in_prelude = True
    raw_chunk = []
    patch = Patch()
    chunk_offset = None

    old_ln = 0
    new_ln = 0

    def process_chunk(chunk, offset, expected_original, expected_revised):
        assert offset is not None
        assert type(expected_original) is int, f"Invalid expected_original type: {type(expected_original)}"
        assert type(expected_revised) is int, f"Invalid expected_revised type: {type(expected_revised)}"
        original_lines, revised_lines = [], []

        for line in chunk:
            tag = line[:1]
            rest = line[1:]
            if tag == ' ':
                revised_lines.append(rest)
                original_lines.append(rest)
            elif tag == '+':
                revised_lines.append(rest)
            elif tag == '-':
                original_lines.append(rest)
            else:
                # Shouldnt've gotten this far
                raise AssertionError(f"Invalid tag got too far: {tag}")
        actual_original, actual_revised = len(original_lines), len(revised_lines)
        if expected_original != actual_original:
            # Sometimes str(expected_original) == str(actual_original) for different numbers!
            assert str(expected_original) != str(actual_original), f"{repr(expected_original)}, {repr(actual_original)}"
            report_error(
                message=f"Expected {expected_original} original lines, but got {actual_original}",
                line_number=offset - 1,
                line=text[offset - 2]
            )
        if expected_revised != actual_revised:
            # Sometimes str(expected_revised) == str(actual_revised) for different numbers!
            assert str(expected_revised) != str(actual_revised), f"{repr(expected_revised)}, {repr(actual_revised)}"
            report_error(
                message=f"Expected {expected_revised} revised lines, but got {actual_revised}",
                line_number=offset - 1,
                line=text[offset - 2]
            )
        for delta in DiffEngine.INSTANCE.diff_chunks(Chunk(old_ln - 1, original_lines), Chunk(new_ln - 1, revised_lines)):
            patch.add_delta(delta)
        del chunk[:]

    expected_original, expected_revised = None, None
    for index, line in enumerate(text):
        line_number = index + 1  # Indexes start at zero, linenos start at 1
        if not lenient and '\n' in line:
            report_error(
                message=f"Line contained newline",
                line_number=line_number,
                line=line
            )
        if in_prelude:
            # Skip leading lines until after we've seen one starting with '+++'
            if line.startswith("+++"):
                in_prelude = False
            continue

        match = __unifiedDiffChunkRe.search(line)
        if match is not None:  # A match is found
            if raw_chunk:
                # Process the lines in the previous chunk
                process_chunk(raw_chunk, chunk_offset, expected_original, expected_revised)
                chunk_offset = None  # Clear the offset
            # Parse the @@ header
            if match.group(1) is None:
                old_ln = 1
            else:
                old_ln = int(match.group(1))
            expected_original = int(match.group(2))
            if match.group(3) is None:
                new_ln = 1
            else:
                new_ln = int(match.group(3))
            expected_revised = int(match.group(4))

            # TODO: Consider error?
            if old_ln == 0:
                old_ln += 1
            if new_ln == 0:
                new_ln += 1
        else:
            if not raw_chunk:
                assert chunk_offset is None
                chunk_offset = line_number
            if line:
                tag = line[:1]
                rest = line[1:]
                if tag in (' ', '+', '-'):
                    raw_chunk.append(tag + rest)
                else:
                    report_error(
                        message=f"Invalid tag {tag}",
                        line_number=line_number,
                        line=line
                    )
            else:
                raw_chunk.append(' ')
    # Process the lines in the final chunk
    process_chunk(raw_chunk, chunk_offset, expected_original, expected_revised)

    return patch


def generate_unified_diff(original_file, revised_file, original_lines, patch, context_size=3):
    """
    Convert the patch into unified diff format

    :param original_file: the name of the original file
    :param revised_file: the name of the changed file
    :param original_lines: the content of the original file
    :param patch: the patch to output
    :param context_size: the number of context lines to put around each difference
    :return: the patch as a list of lines in unified diff format
    """
    return output.generate_unified_diff(original_file, revised_file, original_lines, patch, context_size)
