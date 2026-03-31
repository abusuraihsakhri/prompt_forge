"""
Pipeline orchestrator — ties all 4 stages together.

This is the main entry point for prompt optimization.
"""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from promptforge.core.normalizer import Aggressiveness, normalize
from promptforge.core.parser import parse
from promptforge.core.compressor import compress_sections
from promptforge.core.reconstructor import reconstruct
from promptforge.security.sanitizer import sanitize_input


@dataclass
class OptimizationResult:
    """Result of a prompt optimization pass."""

    # The optimized prompt
    optimized: str

    # Original prompt (sanitized)
    original: str

    # Token counts
    original_tokens: int = 0
    optimized_tokens: int = 0

    # Compression metrics
    compression_ratio: float = 0.0
    savings_percent: float = 0.0
    tokens_saved: int = 0

    # Cost estimation (USD)
    original_cost_estimate: float = 0.0
    optimized_cost_estimate: float = 0.0
    cost_saved: float = 0.0

    # Per-section breakdown
    sections: Dict[str, str] = field(default_factory=dict)

    # Metadata
    model: str = ""
    aggressiveness: str = ""
    processing_time_ms: float = 0.0
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for API/JSON output."""
        return {
            "optimized": self.optimized,
            "original": self.original,
            "metrics": {
                "original_tokens": self.original_tokens,
                "optimized_tokens": self.optimized_tokens,
                "compression_ratio": round(self.compression_ratio, 3),
                "savings_percent": round(self.savings_percent, 1),
                "tokens_saved": self.tokens_saved,
            },
            "cost": {
                "original_estimate_usd": round(self.original_cost_estimate, 6),
                "optimized_estimate_usd": round(self.optimized_cost_estimate, 6),
                "saved_usd": round(self.cost_saved, 6),
            },
            "sections": self.sections,
            "metadata": {
                "model": self.model,
                "aggressiveness": self.aggressiveness,
                "processing_time_ms": round(self.processing_time_ms, 2),
                "warnings": self.warnings,
            },
        }


# Model → format style mapping
MODEL_FORMAT_MAP = {
    "chatgpt": "natural",
    "gpt": "natural",
    "openai": "natural",
    "claude": "structured",
    "anthropic": "structured",
    "gemini": "concise",
    "google": "concise",
}

# Model → aggressiveness mapping
MODEL_AGGRESSIVENESS_MAP = {
    "chatgpt": Aggressiveness.MODERATE,
    "gpt": Aggressiveness.MODERATE,
    "openai": Aggressiveness.MODERATE,
    "claude": Aggressiveness.CONSERVATIVE,
    "anthropic": Aggressiveness.CONSERVATIVE,
    "gemini": Aggressiveness.AGGRESSIVE,
    "google": Aggressiveness.AGGRESSIVE,
}


def _resolve_model_name(model: str) -> str:
    """Normalize model name to a canonical form."""
    model = model.lower().strip()
    aliases = {
        "gpt": "chatgpt", "gpt-4": "chatgpt", "gpt-4o": "chatgpt",
        "gpt-5": "chatgpt", "openai": "chatgpt", "chatgpt": "chatgpt",
        "claude": "claude", "anthropic": "claude",
        "claude-3": "claude", "claude-4": "claude",
        "sonnet": "claude", "opus": "claude", "haiku": "claude",
        "gemini": "gemini", "google": "gemini",
        "gemini-pro": "gemini", "gemini-flash": "gemini",
    }
    return aliases.get(model, model)


def _get_tokenizer(model: str):
    """Get the appropriate tokenizer for a model."""
    from promptforge.tokenizers.tiktoken_counter import TiktokenCounter
    from promptforge.tokenizers.heuristic_counter import HeuristicCounter

    canonical = _resolve_model_name(model)
    if canonical == "chatgpt":
        return TiktokenCounter()
    else:
        return HeuristicCounter()


def _get_pricing(model: str) -> float:
    """Get price per 1M input tokens for cost estimation."""
    canonical = _resolve_model_name(model)
    pricing = {
        "chatgpt": 2.50,   # GPT-4o class pricing
        "claude": 3.00,    # Sonnet class pricing
        "gemini": 1.25,    # Pro class pricing
    }
    return pricing.get(canonical, 2.50)


def optimize(
    prompt: str,
    model: str = "claude",
    aggressiveness: Optional[str] = None,
    format_style: Optional[str] = None,
) -> OptimizationResult:
    """
    Optimize a prompt for a specific LLM platform.

    This is the main entry point for PromptForge.

    Args:
        prompt: The raw prompt to optimize.
        model: Target model platform ("chatgpt", "claude", "gemini").
        aggressiveness: Override compression level ("conservative", "moderate", "aggressive").
            If None, uses the model's default.
        format_style: Override output format ("structured", "xml", "natural", "concise").
            If None, uses the model's default.

    Returns:
        OptimizationResult with optimized prompt and metrics.

    Example:
        >>> result = optimize("Hey Claude, could you please write...", model="claude")
        >>> print(result.optimized)
        >>> print(f"Saved {result.savings_percent:.1f}% tokens")
    """
    start_time = time.perf_counter()
    warnings: List[str] = []

    # --- Input validation ---
    sanitized, sanitize_warnings = sanitize_input(prompt)
    warnings.extend(sanitize_warnings)

    if not sanitized.strip():
        return OptimizationResult(
            optimized="",
            original=prompt,
            warnings=["Empty prompt after sanitization."],
        )

    # --- Resolve model settings ---
    canonical_model = _resolve_model_name(model)

    if canonical_model not in MODEL_FORMAT_MAP:
        warnings.append(
            f"Unknown model '{model}'. Defaulting to 'claude' profile."
        )
        canonical_model = "claude"

    # Determine aggressiveness
    if aggressiveness:
        try:
            aggr = Aggressiveness(aggressiveness.lower())
        except ValueError:
            warnings.append(
                f"Unknown aggressiveness '{aggressiveness}'. Using model default."
            )
            aggr = MODEL_AGGRESSIVENESS_MAP[canonical_model]
    else:
        aggr = MODEL_AGGRESSIVENESS_MAP[canonical_model]

    # Determine output format
    fmt = format_style if format_style else MODEL_FORMAT_MAP[canonical_model]

    # --- Get tokenizer ---
    tokenizer = _get_tokenizer(canonical_model)

    # --- Count original tokens ---
    original_tokens = tokenizer.count(sanitized)

    # === PIPELINE ===

    # Stage 1: Normalize
    normalized = normalize(sanitized, aggressiveness=aggr)

    # Stage 2: Parse into sections
    sections = parse(normalized)

    # Stage 3: Compress
    compressed_sections = compress_sections(sections)

    # Stage 4: Reconstruct
    optimized = reconstruct(compressed_sections, format_style=fmt)

    # === METRICS ===
    optimized_tokens = tokenizer.count(optimized)
    tokens_saved = original_tokens - optimized_tokens
    savings_pct = (tokens_saved / original_tokens * 100) if original_tokens > 0 else 0.0
    compression_ratio = (
        original_tokens / optimized_tokens if optimized_tokens > 0 else 0.0
    )

    # Cost estimation
    price_per_1m = _get_pricing(canonical_model)
    original_cost = (original_tokens / 1_000_000) * price_per_1m
    optimized_cost = (optimized_tokens / 1_000_000) * price_per_1m

    # Warn if compression was too aggressive
    if savings_pct > 60:
        warnings.append(
            "High compression ratio (>60%). Review output for potential semantic loss."
        )

    # If compression actually increased tokens (edge case with very short prompts)
    if optimized_tokens >= original_tokens:
        warnings.append(
            "Prompt is already concise. Optimization did not reduce token count."
        )
        optimized = sanitized  # Return original if compression was counterproductive
        optimized_tokens = original_tokens
        tokens_saved = 0
        savings_pct = 0.0
        compression_ratio = 1.0

    elapsed_ms = (time.perf_counter() - start_time) * 1000

    # Build section breakdown
    section_breakdown = {
        cat: sec.content for cat, sec in compressed_sections.items()
    }

    return OptimizationResult(
        optimized=optimized,
        original=sanitized,
        original_tokens=original_tokens,
        optimized_tokens=optimized_tokens,
        compression_ratio=compression_ratio,
        savings_percent=savings_pct,
        tokens_saved=tokens_saved,
        original_cost_estimate=original_cost,
        optimized_cost_estimate=optimized_cost,
        cost_saved=original_cost - optimized_cost,
        sections=section_breakdown,
        model=canonical_model,
        aggressiveness=aggr.value,
        processing_time_ms=elapsed_ms,
        warnings=warnings,
    )
