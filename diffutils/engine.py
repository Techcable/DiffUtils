from abc import ABCMeta, abstractmethod
from typing import List, TypeVar, Sequence
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

    @property
    @abstractmethod
    def name(self) -> str:
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

    def __repr__(self) -> str:
        import re
        result = []
        for word in re.split('[-_\s]', self.name):
            result.append(word[0].upper())
            result.append(word[1:].lower())
        return ''.join(result) + "DiffEngine"

    INSTANCE: "DiffEngine"

    @staticmethod
    def available_engines() -> Sequence["DiffEngine"]:
        """Get all available DiffEngines, sorted from fastest to slowest"""
        try:
            return tuple(getattr(DiffEngine, '_available_engines'))
        except AttributeError:
            result = []
            try:
                result.append(DiffEngine.create(name='native'))
            except ImportError:
                pass
            result.append(DiffEngine.create(name='plain', hash_optimization=True))
            result.append(DiffEngine.create(name='plain', hash_optimization=False))
            result = tuple(result)
            setattr(DiffEngine, '_available_engines', tuple(result))
            return result

    @staticmethod
    def create(name=None, hash_optimization=True):
        if name is not None and name not in ('native', 'plain', 'native-myers', 'plain-myers'):
            raise ValueError(f"Unknown engine: {name}")
        if name is None or name in ('native', 'native-myers'):
            try:
                from ._native.myers import native_diff
                if not hash_optimization:
                    raise ValueError("Hash optimization is always enabled with native_acceleration!")
                return NativeDiffEngine()
            except ImportError as e:
                if name is None:
                    pass
                else:
                    raise ImportError("Unable to import native implementation!") from e
        assert name is None or name in ('plain-myers', 'plain')
        from ._myers import MyersEngine
        return MyersEngine(hash_optimization=hash_optimization)


class NativeDiffEngine(DiffEngine):
    def diff(self, original, revised) -> Patch:
        from ._native.myers import native_diff
        return native_diff(original, revised)

    @property
    def name(self):
        return "native-myers"


DiffEngine.INSTANCE = DiffEngine.create()
