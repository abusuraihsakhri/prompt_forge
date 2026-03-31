"""
PromptForge — Semantic Prompt Optimizer for LLMs.

A production-grade, model-aware prompt compression and optimization library
for ChatGPT, Claude, and Gemini. Preserves intent, constraints, and structure
while minimizing redundancy and low-information tokens.

Usage:
    from promptforge import optimize

    result = optimize("Your long prompt here...", model="claude")
    print(result.optimized)
    print(f"Saved {result.savings_percent:.1f}% tokens")
"""

__version__ = "1.0.0"
__author__ = "PromptForge Contributors"
__license__ = "MIT"

from promptforge.core.pipeline import optimize, OptimizationResult
from promptforge.models.chatgpt import ChatGPTProfile
from promptforge.models.claude import ClaudeProfile
from promptforge.models.gemini import GeminiProfile

__all__ = [
    "optimize",
    "OptimizationResult",
    "ChatGPTProfile",
    "ClaudeProfile",
    "GeminiProfile",
]
