"""
Stage 3: Compressor — Semantic-preserving text compression.

Replaces verbose phrases with concise equivalents, removes redundancy,
deduplicates constraints, and merges low-value sections.
"""

import re
from typing import Dict, List, Set, Tuple
from promptforge.core.parser import Section


# Verbose → concise phrase mappings.
# Each tuple: (pattern, replacement)
# Patterns are case-insensitive and use word boundaries.
COMPRESSION_RULES: List[Tuple[str, str]] = [
    # Verbal padding
    (r'\bi\s+need\s+you\s+to\b', ''),
    (r'\bi\s+would\s+like\s+you\s+to\b', ''),
    (r'\bi\s+want\s+you\s+to\b', ''),
    (r'\bit\s+is\s+important\s+(?:that|to)\b', ''),
    (r'\bit\s+would\s+be\s+(?:great|nice|helpful)\s+if\b', ''),

    # Verbose constructions → concise
    (r'\bmake\s+sure\s+(?:that\s+)?(?:you\s+)?\b', 'ensure '),
    (r'\bin\s+order\s+to\b', 'to'),
    (r'\bfor\s+the\s+purpose\s+of\b', 'to'),
    (r'\bwith\s+the\s+goal\s+of\b', 'to'),
    (r'\bdue\s+to\s+the\s+fact\s+that\b', 'because'),
    (r'\bas\s+a\s+result\s+of\b', 'because'),
    (r'\bin\s+the\s+event\s+that\b', 'if'),
    (r'\bin\s+case\s+of\b', 'if'),
    (r'\bat\s+this\s+point\s+in\s+time\b', 'now'),
    (r'\bat\s+the\s+present\s+time\b', 'now'),
    (r'\bprior\s+to\b', 'before'),
    (r'\bsubsequent\s+to\b', 'after'),
    (r'\bin\s+the\s+near\s+future\b', 'soon'),
    (r'\bon\s+a\s+regular\s+basis\b', 'regularly'),
    (r'\bin\s+a\s+(?:quick|fast|rapid|speedy)\s+manner\b', 'quickly'),
    (r'\bin\s+a\s+(?:careful|cautious)\s+manner\b', 'carefully'),
    (r'\btake\s+into\s+(?:account|consideration)\b', 'consider'),
    (r'\bhas\s+the\s+ability\s+to\b', 'can'),
    (r'\bis\s+able\s+to\b', 'can'),
    (r'\bis\s+capable\s+of\b', 'can'),
    (r'\bin\s+addition\s+to\b', 'also'),
    (r'\bas\s+well\s+as\b', 'and'),
    (r'\bin\s+spite\s+of\b', 'despite'),
    (r'\bwith\s+regard\s+to\b', 'regarding'),
    (r'\bwith\s+respect\s+to\b', 'regarding'),
    (r'\bin\s+relation\s+to\b', 'about'),
    (r'\bpertaining\s+to\b', 'about'),

    # Quantifier tightening
    (r'\ba\s+lot\s+of\b', 'many'),
    (r'\ba\s+large\s+number\s+of\b', 'many'),
    (r'\ba\s+small\s+number\s+of\b', 'few'),
    (r'\ba\s+significant\s+amount\s+of\b', 'much'),
    (r'\bthe\s+majority\s+of\b', 'most'),
    (r'\ba\s+wide\s+(?:range|variety)\s+of\b', 'various'),
    (r'\beach\s+and\s+every\b', 'every'),

    # Filler adverbs (only in aggressive pairing with compressor)
    (r'\bvery\s+much\b', 'greatly'),
    (r'\bvery\b\s*', ''),
    (r'\bquite\b\s*', ''),
    (r'\brather\b\s*', ''),
    (r'\bsomewhat\b\s*', ''),

    # Redundant meta-commentary
    (r'\b(?:as\s+mentioned\s+(?:above|before|earlier|previously))\b[,.]?\s*', ''),
    (r'\b(?:it\s+(?:should|is)\s+(?:noted|worth\s+noting)\s+that)\b\s*', ''),
    (r'\b(?:it\s+goes\s+without\s+saying\s+that)\b\s*', ''),
    (r'\b(?:needless\s+to\s+say)\b[,.]?\s*', ''),
]


def _apply_compression_rules(text: str) -> str:
    """Apply all verbose→concise phrase replacements."""
    for pattern, replacement in COMPRESSION_RULES:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def _deduplicate_constraints(text: str) -> str:
    """
    Remove duplicate or near-duplicate constraint phrases.

    Detects sentences that convey the same constraint and keeps only the first.
    """
    sentences = re.split(r'(?<=[.!?])\s+', text)
    seen_patterns: Set[str] = set()
    unique_sentences: List[str] = []

    for sentence in sentences:
        if not sentence.strip():
            continue
        # Create a normalized fingerprint for dedup
        # Strip articles, normalize whitespace, lowercase
        fingerprint = re.sub(r'\b(?:a|an|the|this|that|these|those)\b', '', sentence.lower())
        fingerprint = re.sub(r'\s+', ' ', fingerprint).strip()
        fingerprint = re.sub(r'[^\w\s]', '', fingerprint)

        # Check for high similarity with existing fingerprints
        is_dup = False
        for seen in seen_patterns:
            # Simple overlap check: if >70% of words match, it's a duplicate
            words_new = set(fingerprint.split())
            words_seen = set(seen.split())
            if not words_new or not words_seen:
                continue
            overlap = len(words_new & words_seen) / max(len(words_new), len(words_seen))
            if overlap > 0.7:
                is_dup = True
                break

        if not is_dup:
            seen_patterns.add(fingerprint)
            unique_sentences.append(sentence)

    return ' '.join(unique_sentences)


def _merge_trivial_sections(
    sections: Dict[str, Section],
    min_section_length: int = 20
) -> Dict[str, Section]:
    """
    Merge sections that are too small to stand alone into the task section.

    A section with very little content (e.g., "Use JSON.") is better inlined
    into the task description than given its own header.
    """
    merged = {}
    inline_parts: List[str] = []

    for category, section in sections.items():
        if category == "task":
            merged[category] = section
            continue

        if len(section.content) < min_section_length:
            inline_parts.append(section.content)
        else:
            merged[category] = section

    # Append trivial sections to task
    if inline_parts:
        if "task" in merged:
            merged["task"].content += ' ' + ' '.join(inline_parts)
        else:
            merged["task"] = Section(
                category="task",
                content=' '.join(inline_parts)
            )

    return merged


def compress_text(text: str) -> str:
    """
    Compress a single text block.

    Args:
        text: Text to compress.

    Returns:
        Compressed text with verbose phrases shortened and duplicates removed.
    """
    if not text or not text.strip():
        return ""

    text = _apply_compression_rules(text)
    text = _deduplicate_constraints(text)

    # Clean up artifacts
    text = re.sub(r'  +', ' ', text)
    text = re.sub(r'\s+([.,;:!?])', r'\1', text)

    return text.strip()


def compress_sections(
    sections: Dict[str, Section],
    merge_trivial: bool = True,
    min_section_length: int = 20
) -> Dict[str, Section]:
    """
    Compress all sections and optionally merge trivial ones.

    Args:
        sections: Parsed section dictionary.
        merge_trivial: Whether to merge very short sections into task.
        min_section_length: Minimum character length for a standalone section.

    Returns:
        Compressed section dictionary.
    """
    # Compress each section's content
    compressed = {}
    for category, section in sections.items():
        compressed_content = compress_text(section.content)
        if compressed_content:
            compressed[category] = Section(
                category=category,
                content=compressed_content,
                confidence=section.confidence,
                source_indices=section.source_indices,
            )

    # Merge trivial sections
    if merge_trivial:
        compressed = _merge_trivial_sections(compressed, min_section_length)

    return compressed
