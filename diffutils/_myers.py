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
from .core import Patch, Delta, Chunk
from .engine import DiffEngine
from typing import List, Optional, T
import hashlib


class MyersEngine(DiffEngine):
    def __init__(self, hash_optimization=True):
        self.hash_optimization = hash_optimization

    @property
    def name(self):
        return 'plain_myers'

    def diff(self, original, revised):
        if type(original) is not list:
            raise TypeError(f"Original must be a list, not a {type(original)}")
        if type(revised) is not list:
            raise TypeError(f"Revised must be a list, not a {type(revised)}")
        original_hashes: List[bytes] = None
        revised_hashes: List[bytes] = None
        if self.hash_optimization:
            # Since build_path actually doesn't need the elements themselves, we can take their sha256sum to speed up comparison
            # This can improve performance noticably, since hashes usually differ in the first few bytes and there are only 32 bytes at most
            original_hashes = []
            for element in original:
                if type(element) is not str:
                    original_hashes, revised_hashes = None, None
                    break
                h = hashlib.sha256()
                h.update(element.encode('utf-8'))
                original_hashes.append(h.digest())
        if original_hashes is not None:
            revised_hashes = []
            for element in revised:
                if type(element) is not str:
                    original_hashes, revised_hashes = None, None
                    break
                h = hashlib.sha256()
                h.update(element.encode('utf-8'))
                revised_hashes.append(h.digest())
        if original_hashes is not None:
            path = build_path(original_hashes, revised_hashes)
        else:
            path = build_path(original, revised)
        return build_revision(path, original, revised)

    def __repr__(self):
        if self.hash_optimization:
            return "PlainMyersEngine"
        else:
            return "PlainMyersEngine(hash_optimization=False)"


def build_path(original: List[T], revised: List[T]) -> "DiffNode":
    """
    Computes the minimum diffpath that expresses the differences between the original and revised sequences,
    according to Gene Myers differencing algorithm.

    According to the author of the algorithm, a diffpath will always be found, so a RuntimeError shouldn't be thrown.

    :param original: The original sequence.
    :param revised: The revised sequence.
    :return: A minimum {@link DiffNode Path} across the differences graph.
    :exception RuntimeError: if a diff path could not be found.
    """
    original_size = len(original)
    revised_size = len(revised)

    max_size = original_size + revised_size + 1
    size = 1 + 2 * max_size
    middle = size // 2
    diagonal: List[Optional["DiffNode"]] = [None] * size

    diagonal[middle + 1] = create_snake(0, -1, None)
    for d in range(max_size):
        for k in range(-d, d + 1, 2):
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

        diagonal[middle + d - 1] = None

    # According to Myers, this cannot happen
    raise RuntimeError("couldn't find a diff path")


def build_revision(path: "DiffNode", original: List[T], revised: List[T]) -> Patch:
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
        delta = Delta.create(original_chunk, revised_chunk)

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
    __slots__ = "i", "j", "lastSnake", "snake", "prev"
    i: int
    j: int
    lastSnake: Optional["DiffNode"]
    prev: Optional["DiffNode"]
    snake: bool

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
