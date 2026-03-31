"""
Gemini (Google) model profile.

Gemini handles concise, bullet-driven prompts well and has massive
context windows. It excels at multimodal tasks and document synthesis.
"""

from promptforge.models.base import ModelProfile, ModelConfig


class GeminiProfile(ModelProfile):
    """Profile for Google Gemini models (Pro, Flash)."""

    def get_config(self) -> ModelConfig:
        return ModelConfig(
            name="Gemini",
            provider="Google",
            max_context_window=1_000_000,
            pricing_per_1m_input=1.25,
            pricing_per_1m_output=5.00,
            preferred_format="concise",
            compression_aggressiveness=0.7,
            prefers_numbered_constraints=False,
            prefers_xml_tags=False,
            handles_terse=True,
            description=(
                "Gemini handles terse, bullet-driven prompts effectively. "
                "It has massive context windows (1M+ tokens) and excels at "
                "document synthesis and multimodal tasks. "
                "Aggressive compression works well for Gemini."
            ),
        )

    def get_tokenizer(self):
        from promptforge.tokenizers.heuristic_counter import HeuristicCounter
        return HeuristicCounter()
