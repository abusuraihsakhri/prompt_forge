"""
Heuristic token counter for models without public tokenizers.

Provides approximate token counts for Claude and Gemini using
character-ratio estimation calibrated against known benchmarks.
"""

import re
from promptforge.tokenizers.base import BaseTokenCounter


class HeuristicCounter(BaseTokenCounter):
    """
    Approximate token counter using character/word ratio heuristics.

    Calibrated against common English text:
    - ~3.5 characters per token (character-based)
    - ~0.75 tokens per word (word-based)
    - Uses a blend of both for better accuracy

    This is NOT exact for billing purposes. For billing-grade counts,
    use the official API countTokens endpoints for Claude and Gemini.
    """

    def __init__(
        self,
        chars_per_token: float = 3.5,
        tokens_per_word: float = 1.3,
        blend_weight: float = 0.6,
    ):
        """
        Args:
            chars_per_token: Average characters per token for char-based estimation.
            tokens_per_word: Average tokens per word for word-based estimation.
            blend_weight: Weight for character-based estimate (0.0-1.0).
                Word-based gets (1 - blend_weight).
        """
        self._chars_per_token = chars_per_token
        self._tokens_per_word = tokens_per_word
        self._blend_weight = blend_weight

    def count(self, text: str) -> int:
        """Estimate token count using blended heuristic."""
        if not text:
            return 0

        # Character-based estimation
        char_estimate = len(text) / self._chars_per_token

        # Word-based estimation
        words = len(re.findall(r'\S+', text))
        word_estimate = words * self._tokens_per_word

        # Blend both estimates
        blended = (
            self._blend_weight * char_estimate
            + (1 - self._blend_weight) * word_estimate
        )

        return max(1, round(blended))

    def name(self) -> str:
        return "heuristic (char+word blend)"
