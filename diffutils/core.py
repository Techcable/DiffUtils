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

"""Internal Code"""


class Delta:
    """Describes the delta between original and revised texts."""

    class Type(Enum):
        CHANGE = 1
        DELETE = 2
        INSERT = 3

    def __init__(self, original, revised):
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
        raise NotImplementedError

    def apply_to(self, target):
        """
        Applies this delta as the patch for a given target

        :param target: the target to apply to
        :exception PatchFailedException: if the patch could not be applied
        """
        raise NotImplementedError

    def restore(self, target):
        """
        Cancel this delta for a given revised text
        This action is the opposite of patch.

        :param target: the revised text
        """
        raise NotImplementedError

    def __hash__(self):
        return hash((self.original, self.revised))

    def __eq__(self, other):
        if not isinstance(other, Delta):
            return False
        return self.original == other.original and self.revised == other.revised and other.type == self.type


class ChangeDelta(Delta):
    """Describes the change-delta between original and revised texts"""

    def __init__(self, original, revised):
        super().__init__(original, revised)
        self.type = Delta.Type.CHANGE

    def apply_to(self, target):
        self.verify(target)
        position = self.original.position
        size = self.original.size()
        for i in range(size):
            del target[position]
        i = 0
        for line in self.revised.lines:
            target.insert(position + i, line)
            i += 1

    def restore(self, target):
        position = self.revised.position
        size = self.revised.size()
        for i in range(size):
            target.remove(i)
        i = 0
        for line in self.original.lines:
            target.insert(position + i, line)
            i += 1

    def verify(self, target):
        self.original.verify(target)
        if self.original.position > len(target):
            raise PatchFailedException("Incorrect patch for delta: delta original position > target size")


class DeleteDelta(Delta):
    """Describes the delete-delta between original and revised texts."""

    def __init__(self, original, revised):
        super().__init__(original, revised)
        self.type = Delta.Type.DELETE

    def apply_to(self, target):
        self.verify(target)
        position = self.original.position
        size = self.original.size()
        for i in range(size):
            del target[position]

    def restore(self, target):
        position = self.revised.position
        lines = self.original.lines
        for i in range(len(lines)):
            target.insert(position + i, lines[i])

    def verify(self, target):
        self.original.verify(target)


class InsertDelta(Delta):
    """Describes the add-delta between original and revised texts."""

    def __init__(self, original, revised):
        super().__init__(original, revised)
        self.type = Delta.Type.INSERT

    def apply_to(self, target):
        self.verify(target)
        position = self.original.position
        lines = self.revised.lines
        for i in range(len(lines)):
            target.insert(position + i, lines[i])

    def restore(self, target):
        position = self.revised.position
        size = self.revised.size()
        for i in range(size):
            target.remove(position)

    def verify(self, target):
        if self.original.position > len(target):
            raise PatchFailedException("Incorrect patch for delta: delta original position > target size")

class Chunk:
    """Holds the information about the part of text involved in the diff process"""

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
        if self.last() > len(target):
            raise PatchFailedException("Incorrect Chunk: the position of chunk > target size")
        for i in range(self.size()):
            if target[self.position + i] != self.lines[i]:
                raise PatchFailedException(
                    "Incorrect Chunk: the chunk content doesn't match the target at " + str(self.position + i))

    def size(self):
        """
        Returns the number of lines in the chunk

        :return: the number of lines
        """
        return len(self.lines)

    def last(self):
        """
        Returns the index of the last line of the chunk.

        :return: the index of the last line of the chunk
        """
        return self.position + self.size() - 1

    def __hash__(self):
        return hash((self.lines, self.position, self.size()))

    def __eq__(self, other):
        if not isinstance(other, Chunk):
            return False
        return self.lines == other.lines and self.position == other.position


class Patch:
    """A patch holding all deltas between the original and revised texts."""

    def __init__(self):
        self._deltas = list()

    def apply_to(self, target):
        """
        Apply this patch to the given target

        :param target: the target to apply the patch to
        :return: the patched text
        :exception PatchFailedException: if unable to apply
        """
        result = list(target)
        for delta in reversed(self._deltas):
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
        for delta in reversed(self._deltas):
            delta.restore(result)
        return result

    def add_delta(self, delta):
        """
        Add a delta to this patch

        :param delta: the delta to add
        """
        self._deltas.append(delta)
        self._deltas.sort(key=lambda d: d.original.position)

    def get_deltas(self):
        """
        Get a copy of this patch's deltas

        :return: this patch's deltas
        """
        return self._deltas[:]

    def __eq__(self, other):
        if not isinstance(other, Patch):
            return False
        return other._deltas == self._deltas


class PatchFailedException(Exception):
    """Thrown whenever a delta cannot be applied as a patch to a given text."""
