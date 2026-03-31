"""
Tiktoken-based token counter for OpenAI models.

Provides exact token counts that match OpenAI billing.
Falls back to heuristic estimation if tiktoken is not installed.
"""

from promptforge.tokenizers.base import BaseTokenCounter


class TiktokenCounter(BaseTokenCounter):
    """
    Token counter using OpenAI's tiktoken library.

    Uses the o200k_base encoding (GPT-4o and later).
    Falls back to heuristic counting if tiktoken is unavailable.
    """

    def __init__(self, encoding_name: str = "o200k_base"):
        self._encoding_name = encoding_name
        self._encoder = None
        self._fallback = False

        try:
            import tiktoken
            self._encoder = tiktoken.get_encoding(encoding_name)
        except ImportError:
            self._fallback = True
        except Exception:
            self._fallback = True

    def count(self, text: str) -> int:
        """Count tokens using tiktoken or fallback to heuristic."""
        if not text:
            return 0

        if self._encoder is not None:
            return len(self._encoder.encode(text))

        # Fallback: ~4 characters per token for English
        return max(1, len(text) // 4)

    def name(self) -> str:
        if self._fallback:
            return "tiktoken-fallback (heuristic)"
        return f"tiktoken ({self._encoding_name})"
