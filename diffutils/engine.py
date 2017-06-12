from abc import ABCMeta, abstractmethod
from typing import List, TypeVar
from .core import Patch, Chunk

__all__ = ("DiffEngine")

T = TypeVar('T')


class DiffEngine(metaclass=ABCMeta):
    @abstractmethod
    def diff(self, original: List[T], revised: List[T]) -> Patch:
        """
        Computes the difference between the original sequence and the revised sequence.

        :param original: The original text. Must not be None
        :param revised: The revised text. Must not be None
        :return: a patch object representing the difference
        """
        pass

    def diff_chunks(self, original_chunk: Chunk, new_chunk: Chunk):
        """
        Return the deltas that have the minimal diff between the two chunks

        :param original_chunk: the original chunk
        :param new_chunk: the new chunk
        :return: a list of deltas that are the minimum diff between the two chunks
        """
        # Create fake lines so the diff method outputs the correct positions
        fake_original_lines = [""] * original_chunk.position
        fake_new_lines = [""] * original_chunk.position
        patch = self.diff(fake_original_lines + original_chunk.lines, fake_new_lines + new_chunk.lines)
        return patch.deltas

    INSTANCE: "DiffEngine"

    @staticmethod
    def create():
        from ._myers import MyersEngine
        return MyersEngine()


DiffEngine.INSTANCE = DiffEngine.create()
