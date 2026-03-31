"""
Stage 2: Parser — Semantic section extraction.

Classifies sentences and blocks into semantic categories:
task, constraints, context, format, examples, metadata.
Handles both unstructured prose and pre-structured prompts.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass
class Section:
    """A classified semantic section of a prompt."""
    category: str
    content: str
    confidence: float = 1.0
    source_indices: List[int] = field(default_factory=list)


# Intent classification patterns with weights.
# Higher weight = stronger signal for that category.
INTENT_PATTERNS: Dict[str, List[Tuple[str, float]]] = {
    "task": [
        (r'\b(?:write|create|generate|build|implement|develop|design|make|produce)\b', 1.0),
        (r'\b(?:explain|describe|summarize|analyze|compare|evaluate|review)\b', 0.9),
        (r'\b(?:fix|debug|refactor|optimize|improve|update|modify|convert)\b', 0.85),
        (r'\b(?:find|search|identify|detect|extract|parse|calculate)\b', 0.8),
        (r'\b(?:translate|transform|migrate|port|adapt)\b', 0.8),
        (r'\b(?:help|assist|show|tell|give)\b', 0.5),
    ],
    "constraints": [
        (r'\b(?:must|shall|require|mandatory)\b', 1.0),
        (r'\b(?:should|ensure|guarantee|verify)\b', 0.9),
        (r'\b(?:avoid|never|don\'t|do\s+not|prohibit|restrict)\b', 0.95),
        (r'\b(?:limit|maximum|minimum|at\s+(?:least|most)|between|within)\b', 0.85),
        (r'\b(?:only|exclusively|strictly|exactly)\b', 0.8),
        (r'\b(?:important|critical|essential|necessary)\b', 0.7),
        (r'\b(?:without|unless|except|excluding)\b', 0.75),
    ],
    "format": [
        (r'\b(?:format|output|return|respond|reply)\s+(?:as|in|with|using)\b', 1.0),
        (r'\b(?:json|xml|csv|markdown|yaml|html|table|list|array)\b', 0.95),
        (r'\b(?:numbered|bulleted|bullet\s*points?|headings?|sections?)\b', 0.85),
        (r'\b(?:example|sample|template|schema|structure)\s+(?:of|for)\b', 0.7),
        (r'\bformat(?:ted|ting)?\b', 0.8),
        (r'\b(?:output|result|response)\s+(?:should|must|format)\b', 0.9),
    ],
    "context": [
        (r'\b(?:background|context|situation|scenario|given)\b', 0.9),
        (r'\b(?:we\s+(?:have|are|use|need)|our\s+(?:team|project|system))\b', 0.8),
        (r'\b(?:currently|existing|previous|already)\b', 0.7),
        (r'\b(?:for\s+(?:a|an|the|my|our)\b)', 0.6),
        (r'\b(?:assume|assuming|suppose|consider)\b', 0.75),
    ],
    "examples": [
        (r'\b(?:for\s+example|e\.g\.|such\s+as|like\s+this)\b', 1.0),
        (r'\b(?:here\s+is|here\'s)\s+(?:an?\s+)?example\b', 0.95),
        (r'\b(?:sample|instance|illustration|demo)\b', 0.7),
        (r'(?:input|output)\s*[:]\s*[`"\']', 0.85),
        (r'```', 0.6),  # Code blocks often contain examples
    ],
}

# Patterns that detect pre-existing structure (headers, sections)
STRUCTURE_PATTERNS = [
    r'^#{1,6}\s+',           # Markdown headers
    r'^(?:Task|Context|Constraints?|Format|Output|Input|Example|Role|System|Instructions?)\s*[:]\s*',
    r'^\d+\.\s+',           # Numbered lists
    r'^[-*•]\s+',           # Bullet points
    r'^>\s+',               # Blockquotes
]


def _is_prestructured(text: str) -> bool:
    """Detect if the prompt already has explicit structural markers."""
    lines = text.strip().split('\n')
    structure_count = 0
    for line in lines:
        for pattern in STRUCTURE_PATTERNS:
            if re.match(pattern, line.strip(), re.IGNORECASE):
                structure_count += 1
                break
    # If >15% of non-empty lines have structure markers, it's pre-structured
    non_empty = sum(1 for line in lines if line.strip())
    if non_empty == 0:
        return False
    return (structure_count / non_empty) > 0.15


def _classify_sentence(sentence: str) -> Tuple[str, float]:
    """
    Classify a single sentence into a category.

    Returns (category, confidence) tuple.
    """
    best_category = "task"  # Default fallback
    best_score = 0.0

    for category, patterns in INTENT_PATTERNS.items():
        category_score = 0.0
        match_count = 0
        for pattern, weight in patterns:
            if re.search(pattern, sentence, re.IGNORECASE):
                category_score += weight
                match_count += 1
        # Normalize by number of patterns to avoid bias toward categories with more patterns
        if match_count > 0:
            normalized_score = category_score / len(patterns) * match_count
            if normalized_score > best_score:
                best_score = normalized_score
                best_category = category

    confidence = min(best_score, 1.0) if best_score > 0 else 0.3
    return best_category, confidence


def _split_into_segments(text: str) -> List[str]:
    """
    Split text into meaningful segments (sentences or logical blocks).

    Handles:
    - Standard sentence splitting on .!?
    - Preserves code blocks as single segments
    - Preserves list items as single segments
    - Preserves header + content pairs
    """
    segments = []
    lines = text.split('\n')
    current_block = []
    in_code_block = False

    for line in lines:
        stripped = line.strip()

        # Handle code blocks
        if stripped.startswith('```'):
            if in_code_block:
                current_block.append(line)
                segments.append('\n'.join(current_block))
                current_block = []
                in_code_block = False
            else:
                if current_block:
                    segments.append('\n'.join(current_block))
                    current_block = []
                current_block.append(line)
                in_code_block = True
            continue

        if in_code_block:
            current_block.append(line)
            continue

        # Blank line = segment boundary
        if not stripped:
            if current_block:
                segments.append('\n'.join(current_block))
                current_block = []
            continue

        # List items and headers are their own segments
        if re.match(r'^(?:[-*•]|\d+\.)\s+', stripped) or re.match(r'^#{1,6}\s+', stripped):
            if current_block:
                # Check if the current block is a header that should stay with this content
                prev = '\n'.join(current_block).strip()
                if re.match(r'^#{1,6}\s+', prev) or prev.endswith(':'):
                    current_block.append(line)
                    continue
                segments.append(prev)
                current_block = []
            current_block.append(line)
            continue

        current_block.append(line)

    if current_block:
        segments.append('\n'.join(current_block))

    # Further split large prose blocks by sentences
    final_segments = []
    for seg in segments:
        # Don't split code blocks, lists, or short segments
        if seg.startswith('```') or re.match(r'^(?:[-*•]|\d+\.)\s+', seg.strip()):
            final_segments.append(seg)
            continue
        if len(seg) < 100:
            final_segments.append(seg)
            continue

        # Split by sentence boundaries, but keep the delimiter
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', seg)
        final_segments.extend(s for s in sentences if s.strip())

    return [s for s in final_segments if s.strip()]


def _parse_prestructured(text: str) -> Dict[str, Section]:
    """Parse a prompt that already has explicit structure markers."""
    sections: Dict[str, Section] = {}
    current_category = "task"
    current_content: List[str] = []

    # Map common header names to our categories
    header_map = {
        "task": "task", "goal": "task", "objective": "task", "instructions": "task",
        "system": "task", "role": "task", "prompt": "task",
        "constraints": "constraints", "rules": "constraints", "requirements": "constraints",
        "guidelines": "constraints", "limitations": "constraints",
        "format": "format", "output": "format", "response": "format",
        "context": "context", "background": "context", "situation": "context",
        "example": "examples", "examples": "examples", "sample": "examples",
        "input": "context", "metadata": "context",
    }

    lines = text.split('\n')
    for line in lines:
        stripped = line.strip()

        # Check for header patterns
        header_match = re.match(
            r'^(?:#{1,6}\s+)?(?:(\w+))\s*[:]\s*(.*)',
            stripped,
            re.IGNORECASE
        )
        if header_match:
            header_name = header_match.group(1).lower()
            rest = header_match.group(2).strip()

            if header_name in header_map:
                # Save previous section
                if current_content:
                    content = '\n'.join(current_content).strip()
                    if content:
                        if current_category in sections:
                            sections[current_category].content += '\n' + content
                        else:
                            sections[current_category] = Section(
                                category=current_category,
                                content=content
                            )
                    current_content = []

                current_category = header_map[header_name]
                if rest:
                    current_content.append(rest)
                continue

        current_content.append(line)

    # Save final section
    if current_content:
        content = '\n'.join(current_content).strip()
        if content:
            if current_category in sections:
                sections[current_category].content += '\n' + content
            else:
                sections[current_category] = Section(
                    category=current_category,
                    content=content
                )

    return sections


def parse(text: str) -> Dict[str, Section]:
    """
    Extract semantic sections from a prompt.

    Handles both pre-structured and unstructured prompts.

    Args:
        text: Normalized prompt text.

    Returns:
        Dictionary of category -> Section mappings.
    """
    if not text or not text.strip():
        return {}

    # Check for pre-existing structure
    if _is_prestructured(text):
        return _parse_prestructured(text)

    # Unstructured: classify each segment
    segments = _split_into_segments(text)
    section_contents: Dict[str, List[Tuple[str, float, int]]] = {}

    for idx, segment in enumerate(segments):
        category, confidence = _classify_sentence(segment)

        if category not in section_contents:
            section_contents[category] = []
        section_contents[category].append((segment, confidence, idx))

    # Build sections
    sections: Dict[str, Section] = {}
    for category, items in section_contents.items():
        content_parts = [item[0] for item in items]
        avg_confidence = sum(item[1] for item in items) / len(items)
        indices = [item[2] for item in items]

        sections[category] = Section(
            category=category,
            content=' '.join(content_parts),
            confidence=avg_confidence,
            source_indices=indices,
        )

    return sections
