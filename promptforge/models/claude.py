"""
Claude (Anthropic) model profile.

Claude performs best with highly structured, explicit prompts.
It excels at following constraints and benefits from XML tags
and numbered requirements.
"""

from promptforge.models.base import ModelProfile, ModelConfig


class ClaudeProfile(ModelProfile):
    """Profile for Anthropic Claude models (Sonnet, Opus, Haiku)."""

    def get_config(self) -> ModelConfig:
        return ModelConfig(
            name="Claude",
            provider="Anthropic",
            max_context_window=200_000,
            pricing_per_1m_input=3.00,
            pricing_per_1m_output=15.00,
            preferred_format="structured",
            compression_aggressiveness=0.3,
            prefers_numbered_constraints=True,
            prefers_xml_tags=True,
            handles_terse=False,
            description=(
                "Claude relies heavily on explicit constraints and structured formatting. "
                "Over-compression can remove implicit intent that Claude would follow. "
                "Use numbered constraints, clear section headers, and XML tags "
                "for best results. Conservative compression recommended."
            ),
        )

    def get_tokenizer(self):
        from promptforge.tokenizers.heuristic_counter import HeuristicCounter
        return HeuristicCounter()
