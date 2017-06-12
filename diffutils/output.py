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
from typing import Iterator, List


class UnifiedDiffOutput:
    buffer: List[str]

    def __init__(self):
        self.buffer = list()

    def add_context_line(self, line):
        self._write(' ', line)

    def add_remove_line(self, line):
        self._write('-', line)

    def add_insert_line(self, line):
        self._write('+', line)

    def _write(self, prefix, line):
        line = prefix + line
        self.buffer.append(line)

    def add_delta_text(self, delta):
        for line in delta.original.lines:
            self.add_remove_line(line)
        for line in delta.revised.lines:
            self.add_insert_line(line)


def generate_unified_diff(original_file, revised_file, original_lines, patch, context_size=5) -> Iterator[str]:
    """
    A generator that converts the patch into unified diff format

    :param original_file: the name of the original file
    :param revised_file: the name of the changed file
    :param original_lines: the content of the original file
    :param patch: the patch to output
    :param context_size: the number of context lines to put around each difference
    :return: the patch as a list of lines in unified diff format
    """
    if isinstance(original_lines, str):
        original_lines = original_lines.splitlines()
    deltas = patch.deltas
    if not deltas:
        return  # There is nothing in the patch to output
    yield "---" + original_file
    yield "+++" + revised_file

    delta = deltas[0]
    delta_batch = [delta]  # Deltas are batched together and are output together, to get rid of redundant context

    if len(deltas) != 1:
        for next_delta in deltas[1:]:
            position = delta.original.position

            if position + len(delta.original.lines) + context_size >= next_delta.original.position - context_size:
                delta_batch.append(next_delta)
            else:
                yield from process_deltas(original_lines, delta_batch, context_size)
                delta_batch.clear()
                delta_batch.append(next_delta)
            delta = next_delta
    # Process the last batch of deltas
    yield from process_deltas(original_lines, delta_batch, context_size)


def process_deltas(original_lines, deltas, context_size):
    assert context_size >= 0
    buffer = UnifiedDiffOutput()

    original_total = 0  # total lines output from original
    revised_total = 0  # total lines output from revised

    delta = deltas[0]

    # +1 to overcome the 0-offset Position
    original_start = max(1, delta.original.position + 1 - context_size)

    revised_start = max(1, delta.original.position + 1 - context_size)

    context_start = max(0, delta.original.position - context_size)

    # Output the context before the first delta
    for line in original_lines[context_start:delta.original.position]:
        buffer.add_context_line(line)
        original_total += 1
        revised_total += 1

    # Output the first delta
    buffer.add_delta_text(delta)
    original_total += len(delta.original.lines)
    revised_total += len(delta.revised.lines)

    for next_delta in deltas[1:]:
        intermediate_start = delta.original.position + len(delta.original.lines)
        for lineIndex in range(intermediate_start, next_delta.original.position):
            buffer.add_context_line(original_lines[lineIndex])
            original_total += 1
            revised_total += 1
        buffer.add_delta_text(next_delta)
        original_total += len(delta.original.lines)
        revised_total += len(delta.revised.lines)
        delta = next_delta

    context_start = delta.original.position + len(delta.original.lines)
    for lineIndex in range(context_start, min(context_start + context_size, len(original_lines))):
        buffer.add_context_line(original_lines[lineIndex])
        original_total += 1
        revised_total += 1

    yield ''.join(["@@ -", str(original_start), ",", str(original_total), " +", str(revised_start), ",", str(revised_total), " @@"])
    yield from buffer.buffer
