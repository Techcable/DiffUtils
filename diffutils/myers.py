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

"""
A clean-room implementation of <a href="http://www.cs.arizona.edu/people/gene/">Eugene Myers</a> differencing algorithm.

See the paper at http://www.cs.arizona.edu/people/gene/PAPERS/diff.ps
"""
from .core import *


def diff(original, revised):
    """
    Computes the difference between the original sequence and the revised sequence.

    :param original: The original text. Must not be None
    :param revised: The revised text. Must not be None
    :return: a patch object representing the difference
    """
    if original is None:
        raise ValueError("original list must not be None")
    if revised is None:
        raise ValueError("revised list must not be None")
    path = build_path(original, revised)
    return build_revision(path, original, revised)


def build_path(original, revised):
    """
    Computes the minimum diffpath that expresses the differences between the original and revised sequences,
    according to Gene Myers differencing algorithm.

    According to the author of the algorithm, a diffpath will always be found, so a RuntimeError shouldn't be thrown.

    :param original: The original sequence.
    :param revised: The revised sequence.
    :return: A minimum {@link PathNode Path} across the differences graph.
    :exception RuntimeError: if a diff path could not be found.
    """
    original_size = len(original)
    revised_size = len(revised)

    max_size = original_size + revised_size + 1
    size = 1 + 2 * max_size
    middle = size // 2
    diagonal = [None] * size

    diagonal[middle + 1] = create_snake(0, -1, None)
    for d in range(max_size):
        # Grr, IDK the python way to do this (range won't work because of += 2 at the end)
        k = -d
        while k <= d:
            kmiddle = middle + k
            kplus = kmiddle + 1
            kminus = kmiddle - 1
            prev = None

            # For some reason this works, but not the other ways
            if (k == -d) or (k != d and diagonal[kminus].i < diagonal[kplus].i):
                i = diagonal[kplus].i
                prev = diagonal[kplus]
            else:
                i = diagonal[kminus].i + 1
                prev = diagonal[kminus]

            diagonal[kminus] = None

            j = i - k

            node = create_diff_node(i, j, prev)

            # orig and rev are zero-based
            # but the algorithm is one-based
            # that's why there's no +1 when indexing the sequences
            while i < original_size and j < revised_size and original[i] == revised[j]:
                i += 1
                j += 1
            if i > node.i:
                node = create_snake(i, j, node)

            diagonal[kmiddle] = node

            if i >= original_size and j >= revised_size:
                return diagonal[kmiddle]

            k += 2

        diagonal[middle + d - 1] = None

    # According to Myers, this cannot happen
    raise RuntimeError("couldn't find a diff path")


def build_revision(path, original, revised):
    """
    Constructs a {@link Patch} from a difference path.

    :param path: The path.
    :param original: The original sequence.
    :param revised: The revised sequence.
    :exception ValueError: If there is an invalid diffpath
    :return: A Patch corresponding to the path.
    """
    patch = Patch()
    if path.is_snake():
        path = path.prev
    while path is not None and path.prev is not None and path.prev.j >= 0:
        if path.is_snake():
            raise ValueError("Found snake when looking for diff")
        i = path.i
        j = path.j

        path = path.prev
        ianchor = path.i
        janchor = path.j

        original_chunk = Chunk(ianchor, original[ianchor:i])
        revised_chunk = Chunk(janchor, revised[janchor:j])
        delta = None

        if original_chunk.size() is 0 and revised_chunk.size() is not 0:
            delta = InsertDelta(original_chunk, revised_chunk)
        elif original_chunk.size() > 0 and revised_chunk.size() is 0:
            delta = DeleteDelta(original_chunk, revised_chunk)
        else:
            delta = ChangeDelta(original_chunk, revised_chunk)

        patch.add_delta(delta)
        if path.is_snake():
            path = path.prev
    return patch


class DiffNode:
    """
    A diffnode in a diffpath.

    A DiffNode and its previous node mark a delta between two input sequences,
    in other words, two differing sub-sequences (possibly 0 length) between two matching sequences.

    DiffNodes and Snakes allow for compression of diffpaths,
    because each snake is represented by a single Snake node
    and each contiguous series of insertions and deletions is represented by a DiffNode.
    """

    def __init__(self, i, j):
        """
        Creates a new path node

        :param i: The position in the original sequence for the new node.
        :param j: The position in the revised sequence for the new node.
        :param prev: The previous node in the path.
        """
        self.i = i
        self.j = j
        self.lastSnake = None
        self.snake = False

    def is_snake(self):
        """
        Return if the node is a snake

        :return: true if the node is a snake
        """
        return self.snake

    def previous_snake(self):
        """
        Skips sequences of nodes until a snake or bootstrap node is found.
        If this node is a bootstrap node (no previous), this method will return None.

        :return: the first snake or bootstrap node found in the path, or None
        """
        return self.lastSnake


def create_diff_node(i, j, prev):
    node = DiffNode(i, j)
    prev = prev.lastSnake
    node.prev = prev
    if i < 0 or j < 0:
        node.lastSnake = None
    else:
        node.lastSnake = prev.lastSnake
    return node


def create_snake(i, j, prev):
    snake = DiffNode(i, j)
    snake.prev = prev
    snake.lastSnake = snake
    snake.snake = True
    return snake


def diff_chunks(original_chunk, new_chunk):
    """
    Return the deltas that have the minimal diff between the two chunks

    :param original_chunk: the original chunk
    :param new_chunk: the new chunk
    :return: a list of deltas that are the minimum diff between the two chunks
    """
    # Create fake lines so the diff method outputs the correct positions
    fake_original_lines = [""] * original_chunk.position
    fake_new_lines = [""] * original_chunk.position
    patch = diff(fake_original_lines + original_chunk.lines, fake_new_lines + new_chunk.lines)
    return patch.get_deltas()
