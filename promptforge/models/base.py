"""
Abstract base class for model profiles.

Each LLM platform has different preferences for prompt structure,
compression tolerance, and token counting.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ModelConfig:
    """Configuration for a specific LLM model."""

    # Display name
    name: str

    # Provider name
    provider: str

    # Maximum context window in tokens
    max_context_window: int

    # Pricing per 1M tokens (USD)
    pricing_per_1m_input: float
    pricing_per_1m_output: float

    # Preferred prompt structure format
    # One of: "structured", "xml", "natural", "concise"
    preferred_format: str

    # Compression aggressiveness (0.0 = no compression, 1.0 = maximum)
    compression_aggressiveness: float

    # Whether the model benefits from explicit constraint numbering
    prefers_numbered_constraints: bool = False

    # Whether the model benefits from XML tags for sections
    prefers_xml_tags: bool = False

    # Whether the model handles terse/abbreviated prompts well
    handles_terse: bool = False

    # Short description of model strengths
    description: str = ""


class ModelProfile(ABC):
    """Abstract base for model-specific optimization profiles."""

    @abstractmethod
    def get_config(self) -> ModelConfig:
        """Return the model configuration."""
        ...

    @abstractmethod
    def get_tokenizer(self):
        """Return the appropriate tokenizer for this model."""
        ...

    def estimate_cost(self, token_count: int) -> float:
        """Estimate cost for a given token count (input only)."""
        config = self.get_config()
        return (token_count / 1_000_000) * config.pricing_per_1m_input
