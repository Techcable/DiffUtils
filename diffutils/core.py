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
from enum import Enum
from abc import ABCMeta, abstractmethod
from typing import List, Union, Tuple
import operator

"""Internal Code"""

__all__ = (
    "Delta",
    "Chunk",
    "Patch",
    "PatchFailedException"
)


class Delta(metaclass=ABCMeta):
    """Describes the delta between original and revised texts."""
    __slots__ = "original", "revised"

    class Type(Enum):
        CHANGE = 1
        DELETE = 2
        INSERT = 3

    @property
    @abstractmethod
    def type(self) -> Type:
        pass

    def __init__(self, original: "Chunk", revised: "Chunk"):
        """
        Construct the delta for original and revised chunks

        :param original: Chunk describing the original text. Must not be None
        :param revised : Chunk describing the revised  text. Must not be None
        """
        if original is None:
            raise ValueError("original must not be null")
        if revised is None:
            raise ValueError("revised must not be null")
        self.original = original
        self.revised = revised

    def verify(self, target):
        """
        Verifies that this delta can be used to patch the given text.

        :param target: target the target to verify
        :exception PatchFailedException: if the patch is not valid
        """
        original, revised = self.original, self.revised
        if original:
            original.verify(target)
        if revised and original.position > len(target):
            raise PatchFailedException("Incorrect patch for delta: delta original position > target size")

    def apply_to(self, target):
        """
        Applies this delta as the patch for a given target

        :param target: the target to apply to
        :exception PatchFailedException: if the patch could not be applied
        """
        original, revised = self.original, self.revised
        self.verify(target)
        position = original.position
        size = len(original)
        if original:
            # NOTE: This was a call to remove in a loop, which was O(n^2)
            # In my deffense I didn't understand slicing, so I didn't know how to do it fast
            del target[position:position + size]
        if revised:
            # NOTE: This was a call to insert in a loop, which was O(n^2)
            # In my defense I didn't understand slicing, so I didn't know how to do it fast
            target[position:position] = revised.lines

    def restore(self, target):
        """
        Cancel this delta for a given revised text
        This action is the opposite of patch.

        :param target: the revised text
        """
        self.reverse().apply_to(target)

    def reverse(self) -> "Delta":
        return Delta.create(original=self.revised, revised=self.original)

    def __hash__(self):
        return hash((self.original, self.revised))

    def __eq__(self, other):
        if isinstance(other, Delta):
            return self.original == other.original and self.revised == other.revised
        else:
            return NotImplemented

    @staticmethod
    def create(original: "Chunk", revised: "Chunk") -> "Delta":
        """Create a delta of the apropriate type, based on the original and revised chunks"""
        assert type(original) is Chunk and type(revised) is Chunk
        if original:
            if revised:
                delta_type = ChangeDelta
            else:
                delta_type = DeleteDelta
        elif revised:
            delta_type = InsertDelta
        else:
            raise ValueError("Empty deltas!")
        return delta_type(original, revised)


class ChangeDelta(Delta):
    """Describes the change-delta between original and revised texts"""

    # NOTE: We inherit almost everything, and we're mostly just here for backwards compat

    @property
    def type(self):
        return Delta.Type.CHANGE


class DeleteDelta(Delta):
    """Describes the delete-delta between original and revised texts."""

    # NOTE: We inherit almost everything, and we're mostly just here for backwards compat

    @property
    def type(self):
        return Delta.Type.DELETE


class InsertDelta(Delta):
    """Describes the add-delta between original and revised texts."""

    # NOTE: We inherit almost everything, and we're mostly just here for backwards compat

    @property
    def type(self):
        return Delta.Type.INSERT


class Chunk:
    """Holds the information about the part of text involved in the diff process"""
    __slots__ = "position", "lines"

    def __init__(self, position, lines):
        """Creates a chunk and saves a copy of affected lines"""
        self.position = position
        self.lines = lines

    def verify(self, target):
        """
        Verifies that this chunk's saved text matches the corresponding text in the target.

        :param target: the sequence to verify against.
        :exception PatchFailedException: If doesn't match
        """
        if self.last > len(target):
            raise PatchFailedException("Incorrect Chunk: the position of chunk > target size")
        position = self.position
        for (offset, expected) in enumerate(self.lines):
            index = position + offset
            actual = target[index]
            if actual != expected:
                raise PatchFailedException(
                    f"Incorrect Chunk: the chunk content {repr(expected)} doesn't match the target {repr(actual)} at {index}"
                )

    def __len__(self):
        """
        Returns the number of lines in the chunk

        :return: the number of lines
        """
        return len(self.lines)

    @property
    def last(self):
        """
        Returns the index of the last line of the chunk.

        :return: the index of the last line of the chunk
        """
        return self.position + len(self.lines) - 1

    def __hash__(self):
        return hash((self.lines, self.position))

    def __eq__(self, other):
        if not isinstance(other, Chunk):
            return False
        return self.lines == other.lines and self.position == other.position


class Patch:
    """A patch holding all deltas between the original and revised texts."""
    __slots__ = "_deltas"
    _deltas: Union[Tuple[Delta, ...], List[Delta]]

    def __init__(self):
        self._deltas = list()

    def apply_to(self, target):
        """
        Apply this patch to the given target

        :param target: the target to apply the patch to
        :return: the patched text
        :exception PatchFailedException: if unable to apply
        """
        if isinstance(target, str):
            target = target.splitlines()
        result = list(target)
        for delta in reversed(self.deltas):
            delta.apply_to(result)
        return result

    def restore(self, target):
        """
        Restore the text to original.
        Opposite of the applyTo() method.

        :param target: the changed text
        :return: the original text
        """
        result = list(target)
        for delta in reversed(self.deltas):
            delta.restore(result)
        return result

    def add_delta(self, delta):
        """
        Add a delta to this patch

        :param delta: the delta to add
        """
        # NOTE: We defer sorting till the first access to avoid O(n^2) behavior
        deltas = self._deltas
        if type(deltas) is not list:
            # We were a tuple since people were reading us, copy back to a list now that insertions are happening
            self._deltas = deltas = list(deltas)
        deltas.append(delta)

    @property
    def deltas(self) -> Tuple[Delta, ...]:
        # NOTE: Make defensive copy, and transparently sort the array on first access
        # To the caller, this class appears to have O(1) insertions while maintaining the sort invariant
        # This copy/sort should only happen rarely, since the Patch is usually only inserted to at first
        deltas = self._deltas
        if type(deltas) is not tuple:
            # NOTE: Mypy is stupid and doesn't recognize our speed hack
            deltas.sort(key=operator.attrgetter('original.position'))  # type: ignore
            self._deltas = deltas = tuple(deltas)
        return deltas  # type: ignore

    def __eq__(self, other):
        if not isinstance(other, Patch):
            return False
        return other._deltas == self._deltas


class PatchFailedException(Exception):
    """Thrown whenever a delta cannot be applied as a patch to a given text."""
