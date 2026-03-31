"""
ChatGPT (OpenAI) model profile.

GPT models tolerate more verbosity and prefer natural, conversational prompts.
They excel at following structured output schemas (JSON, tables).
"""

from promptforge.models.base import ModelProfile, ModelConfig


class ChatGPTProfile(ModelProfile):
    """Profile for OpenAI GPT models (ChatGPT, GPT-4o, GPT-5)."""

    def get_config(self) -> ModelConfig:
        return ModelConfig(
            name="ChatGPT",
            provider="OpenAI",
            max_context_window=128_000,
            pricing_per_1m_input=2.50,
            pricing_per_1m_output=10.00,
            preferred_format="natural",
            compression_aggressiveness=0.5,
            prefers_numbered_constraints=False,
            prefers_xml_tags=False,
            handles_terse=False,
            description=(
                "GPT models handle conversational prompts well. "
                "They tolerate moderate verbosity and excel at following "
                "explicit output format schemas (JSON, tables). "
                "Use natural language with clear structure."
            ),
        )

    def get_tokenizer(self):
        from promptforge.tokenizers.tiktoken_counter import TiktokenCounter
        return TiktokenCounter()
