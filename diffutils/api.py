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
from diffutils import myers
from diffutils.core import *

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
    return myers.diff(original, revised)


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

    Warning, this method outputs a 'ChangeDelta', which

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

        for raw_line in chunk:
            tag = raw_line[0]
            rest = raw_line[1]
            if tag is ' ' or tag is '-':
                old_chunk_lines.append(rest)
            if tag is ' ' or tag is '+':
                new_chunk_lines.append(rest)
        for delta in myers.diff_chunks(Chunk(old_ln - 1, old_chunk_lines), Chunk(new_ln - 1, new_chunk_lines)):
            patch.add_delta(delta)
        chunk.clear()

    for line in text:
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
                if tag is ' ' or tag is '+' or tag is '-':
                    raw_chunk.append([tag, rest])
            else:
                raw_chunk.append([' ', ''])
    # Process the lines in the final chunk
    process_chunk(raw_chunk)

    return patch


def generate_unified_diff(original_file, revised_file, original_lines, patch, context_size):
    """
    Convert the patch into unified diff format

    :param original_file: the name of the original file
    :param revised_file: the name of the changed file
    :param original_lines: the content of the original file
    :param patch: the patch to output
    :param context_size: the number of context lines to put around each difference
    :return: the patch as a list of lines in unified diff format
    """
    if isinstance(original_lines, str):
        original_lines = original_lines.splitlines()
    deltas = patch.get_deltas()  # patch.get_deltas() does a defensive copy, so lets make sure that is only done once
    if len(deltas) is 0:
        return list()  # There is nothing in the patch to output
    result = list()
    result.append("---" + original_file)
    result.append("+++" + revised_file)

    delta = deltas[0]
    delta_batch = [delta]  # Deltas are batched together and are output together, to get rid of redundant context

    if len(deltas) is not 1:
        for i in range(1, len(deltas)):
            position = delta.original.position
            next_delta = deltas[i]

            if position + len(delta.original.lines) + context_size >= next_delta.original.position - context_size:
                delta_batch.append(next_delta)
            else:
                result.extend(__process_deltas(original_lines, deltas, context_size))
                delta_batch.clear()
                delta_batch.append(next_delta)
            delta = next_delta
    # Process the last batch of deltas
    result.extend(__process_deltas(original_lines, delta_batch, context_size))
    return result


"""Utilities"""


def __process_deltas(original_lines, deltas, context_size):
    def add_delta_text(delta, buffer):
        for line in delta.original.lines:
            buffer.append("-" + line)
        for line in delta.revised.lines:
            buffer.append("+" + line)

    buffer = list()
    original_total = 0  # total lines output from original
    revised_total = 0  # total lines output from revised

    delta = deltas[0]

    # +1 to overcome the 0-offset Position
    original_start = delta.original.position + 1 - context_size
    if original_start < 1:
        original_start = 1

    revised_start = delta.original.position + 1 - context_size
    if revised_start < 1:
        revised_start = 1

    context_start = delta.original.position - context_size
    if context_start < 0:
        context_start = 0  # There are no lines before line 0

    # Output the context before the first delta
    for lineIndex in range(context_start, delta.original.position):
        buffer.append(" " + original_lines[lineIndex])
        original_total += 1
        revised_total += 1

    # Output the first delta
    add_delta_text(delta, buffer)
    original_total += len(delta.original.lines)
    revised_total += len(delta.revised.lines)

    for delta_index in range(1, len(deltas)):
        next_delta = deltas[delta_index]
        intermediate_start = delta.original.position + len(delta.original.lines)
        for lineIndex in range(intermediate_start, next_delta.original.position):
            buffer.append(" " + original_lines[lineIndex])
            original_total += 1
            revised_total += 1
        add_delta_text(next_delta, buffer)
        original_total += len(delta.original.lines)
        revised_total += len(delta.revised.lines)
        delta = next_delta

    context_start = delta.original.position + len(delta.original.lines)
    for lineIndex in range(context_start, min(context_start + context_size, len(original_lines))):
        buffer.append(" " + original_lines[lineIndex])
        original_total += 1
        revised_total += 1

    buffer.insert(0, "@@ -" + str(original_start) + "," + str(original_total) +
                  " +" + str(revised_start) + "," + str(revised_total) + " @@")

    return buffer
