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
from diffutils.core import *
from diffutils.engine import DiffEngine

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
        original = revised.splitlines()
    patch.restore(revised)


def parse_unified_diff(text):
    """
    Parse the given text in unified format into a patch.

    :param text: the unified diff
    :return: the parsed patch
    """
    if isinstance(text, str):
        text = text.splitlines()
    in_prelude = True
    raw_chunk = list()
    patch = Patch()

    old_ln = 0
    new_ln = 0

    def process_chunk(chunk):
        if len(chunk) is 0:
            return
        old_chunk_lines = list()
        new_chunk_lines = list()

        for line in chunk:
            tag = line[:1]
            rest = line[1:]
            if tag == ' ':
                new_chunk_lines.append(rest)
                old_chunk_lines.append(rest)
            elif tag == '+':
                new_chunk_lines.append(rest)
            elif tag == '-':
                old_chunk_lines.append(rest)
        for delta in DiffEngine.INSTANCE.diff_chunks(Chunk(old_ln - 1, old_chunk_lines), Chunk(new_ln - 1, new_chunk_lines)):
            patch.add_delta(delta)
        del chunk[:]

    for line in text:
        assert '\n' not in line, f"Newline in line: {repr(line)}"
        if in_prelude:
            # Skip leading lines until after we've seen one starting with '+++'
            if line.startswith("+++"):
                in_prelude = False
            continue

        match = __unifiedDiffChunkRe.search(line)
        if match is not None:  # A match is found
            # Process the lines in the previous chunk
            process_chunk(raw_chunk)

            # Parse the @@ header
            if match.group(1) is None:
                old_ln = 1
            else:
                old_ln = int(match.group(1))
            if match.group(3) is None:
                new_ln = 1
            else:
                new_ln = int(match.group(3))

            if old_ln is 0:
                old_ln += 1
            if new_ln is 0:
                new_ln += 1
        else:
            if len(line) > 0:
                tag = line[:1]
                rest = line[1:]
                if tag == ' ' or tag == '+' or tag == '-':
                    raw_chunk.append(tag + rest)
            else:
                raw_chunk.append([' ', ''])
    # Process the lines in the final chunk
    process_chunk(raw_chunk)

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
