"""
Input sanitizer — security boundary for all incoming text.

Validates input, strips dangerous patterns, and enforces size limits.
No eval(), no pickle, no subprocess. Defense in depth.
"""

import re
import html
from typing import List, Tuple

# Maximum input length (500K characters ≈ ~125K tokens)
MAX_INPUT_LENGTH = 500_000

# Minimum meaningful input
MIN_INPUT_LENGTH = 3

# Patterns that look like prompt injection attempts
INJECTION_PATTERNS = [
    # Attempts to override system instructions
    r'(?i)ignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions?',
    r'(?i)disregard\s+(?:all\s+)?(?:previous|prior|above)',
    r'(?i)forget\s+(?:everything|all)',
    r'(?i)new\s+instructions?\s*[:.]',
    r'(?i)system\s*(?:prompt|message)\s*[:.]',
    r'(?i)you\s+are\s+now\s+(?:a|an)',
    r'(?i)act\s+as\s+if\s+(?:you|your)\s+(?:previous|prior)',
    # Attempts to extract system prompts
    r'(?i)(?:show|reveal|print|output|display)\s+(?:your\s+)?system\s+prompt',
    r'(?i)what\s+(?:are|is)\s+your\s+(?:system\s+)?instructions?',
]


def _check_length(text: str) -> Tuple[str, List[str]]:
    """Validate and enforce input length limits."""
    warnings = []

    if len(text) > MAX_INPUT_LENGTH:
        warnings.append(
            f"Input truncated from {len(text):,} to {MAX_INPUT_LENGTH:,} characters."
        )
        text = text[:MAX_INPUT_LENGTH]

    return text, warnings


def _strip_html_tags(text: str) -> str:
    """Defang HTML to prevent XSS in downstream rendering contexts."""
    # Defang all HTML brackets into entities rather than stripping arbitrarily
    # This preserves the content for LLMs while rendering it inert for browsers
    return html.escape(text, quote=False)


def _detect_injection(text: str) -> List[str]:
    """
    Detect potential prompt injection patterns.

    Does NOT block the text — only warns. The user may legitimately
    want to discuss or analyze prompt injections.
    """
    warnings = []
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text):
            warnings.append(
                "⚠ Potential prompt injection pattern detected. "
                "Content preserved but flagged for review."
            )
            break  # One warning is sufficient
    return warnings


def _strip_null_bytes(text: str) -> str:
    """Remove null bytes that could cause issues in processing."""
    return text.replace('\x00', '')


def sanitize_input(text: str) -> Tuple[str, List[str]]:
    """
    Sanitize raw user input before processing.

    Security measures:
    - Length validation and truncation
    - Null byte removal
    - HTML/script tag stripping
    - Prompt injection detection (warning, not blocking)

    Args:
        text: Raw user input.

    Returns:
        Tuple of (sanitized_text, list_of_warnings).
    """
    warnings: List[str] = []

    if not text:
        return "", ["Empty input received."]

    if len(text.strip()) < MIN_INPUT_LENGTH:
        return text.strip(), ["Input too short for meaningful optimization."]

    # Strip null bytes
    text = _strip_null_bytes(text)

    # Enforce length limits
    text, length_warnings = _check_length(text)
    warnings.extend(length_warnings)

    # Strip HTML tags (defense against XSS in web UI)
    text = _strip_html_tags(text)

    # Detect injection patterns (warn, don't block)
    injection_warnings = _detect_injection(text)
    warnings.extend(injection_warnings)

    return text, warnings
