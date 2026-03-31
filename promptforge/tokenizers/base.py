"""
Abstract base tokenizer interface.
"""

from abc import ABC, abstractmethod


class BaseTokenCounter(ABC):
    """Abstract base class for token counters."""

    @abstractmethod
    def count(self, text: str) -> int:
        """
        Count the number of tokens in the given text.

        Args:
            text: Input text to tokenize.

        Returns:
            Number of tokens.
        """
        ...

    @abstractmethod
    def name(self) -> str:
        """Return the name of this tokenizer."""
        ...
