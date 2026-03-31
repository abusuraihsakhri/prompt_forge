"""
Stage 1: Normalizer — Text normalization and filler removal.

Handles Unicode normalization, whitespace collapse, and safe removal of
low-information filler words while preserving grammar and meaning.
"""

import re
import unicodedata
from dataclasses import dataclass
from enum import Enum
from typing import List


class Aggressiveness(Enum):
    """Compression aggressiveness levels."""
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


@dataclass
class FillerPattern:
    """A filler pattern with its aggressiveness threshold."""
    pattern: str
    level: Aggressiveness
    replacement: str = ""


# Ordered from safest to most aggressive removal.
# Each pattern uses word boundaries to prevent mid-word matches.
FILLER_PATTERNS: List[FillerPattern] = [
    # --- CONSERVATIVE: Universally safe removals ---
    FillerPattern(r'\b(?:hey|hi|hello)\b[,.]?\s*', Aggressiveness.CONSERVATIVE),
    FillerPattern(r'\bthanks?\b[!.]?\s*', Aggressiveness.CONSERVATIVE),
    FillerPattern(r'\bthank\s+you\b[!.]?\s*', Aggressiveness.CONSERVATIVE),
    FillerPattern(r'\bplease\b\s*', Aggressiveness.CONSERVATIVE),
    FillerPattern(r'\bkindly\b\s*', Aggressiveness.CONSERVATIVE),

    # --- MODERATE: Verbal crutches and hedging ---
    FillerPattern(r'\bcould\s+you\b\s*', Aggressiveness.MODERATE),
    FillerPattern(r'\bwould\s+you\b\s*', Aggressiveness.MODERATE),
    FillerPattern(r'\bcan\s+you\b\s*', Aggressiveness.MODERATE),
    FillerPattern(r'\bi\s+need\s+you\s+to\b\s*', Aggressiveness.MODERATE),
    FillerPattern(r'\bi\s+would\s+like\s+you\s+to\b\s*', Aggressiveness.MODERATE),
    FillerPattern(r'\bi\s+want\s+you\s+to\b\s*', Aggressiveness.MODERATE),
    FillerPattern(r'\bif\s+possible\b[,.]?\s*', Aggressiveness.MODERATE),
    FillerPattern(r'\bif\s+you\s+don\'t\s+mind\b[,.]?\s*', Aggressiveness.MODERATE),

    # --- AGGRESSIVE: Hedging and qualifiers ---
    FillerPattern(r'\bjust\b\s*', Aggressiveness.AGGRESSIVE),
    FillerPattern(r'\bbasically\b[,.]?\s*', Aggressiveness.AGGRESSIVE),
    FillerPattern(r'\bessentially\b[,.]?\s*', Aggressiveness.AGGRESSIVE),
    FillerPattern(r'\bactually\b[,.]?\s*', Aggressiveness.AGGRESSIVE),
    FillerPattern(r'\bliterally\b\s*', Aggressiveness.AGGRESSIVE),
    FillerPattern(r'\bsimply\b\s*', Aggressiveness.AGGRESSIVE),
    FillerPattern(r'\breally\b\s*', Aggressiveness.AGGRESSIVE),
]


def _aggressiveness_to_int(level: Aggressiveness) -> int:
    """Convert aggressiveness enum to ordinal for comparison."""
    order = {
        Aggressiveness.CONSERVATIVE: 0,
        Aggressiveness.MODERATE: 1,
        Aggressiveness.AGGRESSIVE: 2,
    }
    return order[level]


def normalize_unicode(text: str) -> str:
    """Normalize Unicode to NFC form and strip zero-width characters."""
    text = unicodedata.normalize("NFC", text)
    # Remove zero-width spaces, joiners, and other invisible characters
    text = re.sub(r'[\u200b\u200c\u200d\u2060\ufeff]', '', text)
    return text


def collapse_whitespace(text: str) -> str:
    """Normalize whitespace without destroying intentional formatting."""
    # Collapse runs of blank lines to at most 2 newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Collapse horizontal whitespace (tabs, multiple spaces) within lines
    text = re.sub(r'[ \t]{2,}', ' ', text)
    # Remove trailing whitespace per line
    text = re.sub(r'[ \t]+$', '', text, flags=re.MULTILINE)
    # Remove leading whitespace on blank lines
    text = re.sub(r'^[ \t]+$', '', text, flags=re.MULTILINE)
    return text


def remove_fillers(text: str, level: Aggressiveness = Aggressiveness.MODERATE) -> str:
    """
    Remove filler words/phrases up to the specified aggressiveness level.

    Uses word-boundary-guarded patterns to prevent mid-word corruption.
    """
    threshold = _aggressiveness_to_int(level)

    for fp in FILLER_PATTERNS:
        if _aggressiveness_to_int(fp.level) <= threshold:
            text = re.sub(fp.pattern, fp.replacement, text, flags=re.IGNORECASE)

    return text


def fix_punctuation(text: str) -> str:
    """Clean up punctuation artifacts left after filler removal."""
    # Remove double spaces
    text = re.sub(r'  +', ' ', text)
    # Fix space before punctuation
    text = re.sub(r'\s+([.,;:!?])', r'\1', text)
    # Fix double punctuation
    text = re.sub(r'([.,;:!?])\s*\1+', r'\1', text)
    # Capitalize after sentence-ending punctuation
    text = re.sub(
        r'([.!?])\s+([a-z])',
        lambda m: m.group(1) + ' ' + m.group(2).upper(),
        text
    )
    # Fix sentences starting with lowercase after removal
    lines = text.split('\n')
    result = []
    for line in lines:
        stripped = line.strip()
        if stripped and stripped[0].islower() and not stripped.startswith(('- ', '* ', '• ')):
            stripped = stripped[0].upper() + stripped[1:]
        result.append(stripped)
    text = '\n'.join(result)
    return text


def normalize(
    text: str,
    aggressiveness: Aggressiveness = Aggressiveness.MODERATE
) -> str:
    """
    Full normalization pipeline.

    Args:
        text: Raw input text.
        aggressiveness: How aggressively to remove filler content.

    Returns:
        Normalized text with filler removed and whitespace cleaned.
    """
    if not text or not text.strip():
        return ""

    text = normalize_unicode(text)
    text = text.strip()
    text = remove_fillers(text, level=aggressiveness)
    text = collapse_whitespace(text)
    text = fix_punctuation(text)
    return text.strip()
