"""
Stage 4: Reconstructor — Model-aware prompt assembly.

Takes classified and compressed sections and reconstructs them into
an optimized prompt format tailored  to the target LLM platform.
"""

import re
from typing import Dict, List
from promptforge.core.parser import Section


# Section display order (priority)
SECTION_ORDER = ["task", "context", "constraints", "examples", "format"]

# Section display labels per format style
SECTION_LABELS = {
    "task": {"structured": "Task", "xml": "task", "natural": ""},
    "context": {"structured": "Context", "xml": "context", "natural": "Background:"},
    "constraints": {"structured": "Constraints", "xml": "constraints", "natural": "Requirements:"},
    "examples": {"structured": "Examples", "xml": "examples", "natural": "Examples:"},
    "format": {"structured": "Output Format", "xml": "output_format", "natural": "Output:"},
}


def _reconstruct_structured(sections: Dict[str, Section]) -> str:
    """
    Reconstruct as a clean, structured prompt with labeled sections.

    Best for: Claude (prefers explicit structure and constraints).

    Format:
        Task: ...
        Context: ...
        Constraints:
        - ...
        Output Format: ...
    """
    parts: List[str] = []

    for key in SECTION_ORDER:
        if key not in sections:
            continue
        section = sections[key]
        label = SECTION_LABELS[key]["structured"]
        content = section.content.strip()

        if not content:
            continue

        if key == "constraints":
            # Break constraints into bullet points for clarity
            constraint_items = _extract_constraint_items(content)
            if len(constraint_items) > 1:
                bullets = '\n'.join(f"- {item}" for item in constraint_items)
                parts.append(f"{label}:\n{bullets}")
            else:
                parts.append(f"{label}: {content}")
        elif key == "task":
            parts.append(f"{label}: {content}")
        else:
            parts.append(f"{label}: {content}")

    return '\n\n'.join(parts)


def _reconstruct_xml(sections: Dict[str, Section]) -> str:
    """
    Reconstruct using XML-style tags.

    Best for: Claude (native XML tag support for section boundaries).

    Format:
        <task>...</task>
        <constraints>...</constraints>
        <output_format>...</output_format>
    """
    parts: List[str] = []

    for key in SECTION_ORDER:
        if key not in sections:
            continue
        section = sections[key]
        tag = SECTION_LABELS[key]["xml"]
        content = section.content.strip()

        if not content:
            continue

        if key == "constraints":
            constraint_items = _extract_constraint_items(content)
            if len(constraint_items) > 1:
                inner = '\n'.join(f"  - {item}" for item in constraint_items)
                parts.append(f"<{tag}>\n{inner}\n</{tag}>")
            else:
                parts.append(f"<{tag}>{content}</{tag}>")
        else:
            parts.append(f"<{tag}>{content}</{tag}>")

    return '\n\n'.join(parts)


def _reconstruct_natural(sections: Dict[str, Section]) -> str:
    """
    Reconstruct as natural prose with light formatting.

    Best for: ChatGPT (tolerates conversational flow, prefers natural phrasing).
    """
    parts: List[str] = []

    for key in SECTION_ORDER:
        if key not in sections:
            continue
        section = sections[key]
        content = section.content.strip()

        if not content:
            continue

        if key == "task":
            # Task is the opening statement, no label
            parts.append(content)
        elif key == "constraints":
            constraint_items = _extract_constraint_items(content)
            if len(constraint_items) > 1:
                bullets = '\n'.join(f"- {item}" for item in constraint_items)
                parts.append(f"Requirements:\n{bullets}")
            else:
                parts.append(content)
        else:
            label = SECTION_LABELS[key]["natural"]
            if label:
                parts.append(f"{label} {content}")
            else:
                parts.append(content)

    return '\n\n'.join(parts)


def _reconstruct_concise(sections: Dict[str, Section]) -> str:
    """
    Reconstruct as ultra-concise bullet-driven format.

    Best for: Gemini (handles terse prompts well, large context windows).
    """
    parts: List[str] = []

    for key in SECTION_ORDER:
        if key not in sections:
            continue
        section = sections[key]
        content = section.content.strip()

        if not content:
            continue

        if key == "task":
            # Single-line task statement
            parts.append(f"→ {content}")
        elif key == "constraints":
            constraint_items = _extract_constraint_items(content)
            bullets = '\n'.join(f"• {item}" for item in constraint_items)
            parts.append(bullets)
        elif key == "format":
            parts.append(f"Output: {content}")
        elif key == "examples":
            parts.append(f"Ex: {content}")
        else:
            parts.append(content)

    return '\n'.join(parts)


def _extract_constraint_items(text: str) -> List[str]:
    """
    Extract individual constraint items from a constraint block.

    Handles:
    - Sentence-separated constraints
    - Pre-existing bullet points
    - "and" / "," separated constraint lists
    """
    # If already bulleted, extract items
    bullet_match = re.findall(r'(?:^|\n)\s*[-*•]\s+(.+)', text)
    if bullet_match:
        return [item.strip() for item in bullet_match if item.strip()]

    # Split by sentence boundaries
    sentences = re.split(r'(?<=[.!?])\s+', text)
    items = [s.strip().rstrip('.') for s in sentences if s.strip()]

    # If only one sentence, try splitting on "and" for compound constraints
    if len(items) == 1:
        parts = re.split(r'\s*(?:,\s*and\s+|,\s+and\s+|\s+and\s+)', items[0])
        if len(parts) > 1:
            items = [p.strip() for p in parts if p.strip()]

    return items if items else [text.strip()]


# Available reconstruction formats mapped to their functions
FORMATS = {
    "structured": _reconstruct_structured,
    "xml": _reconstruct_xml,
    "natural": _reconstruct_natural,
    "concise": _reconstruct_concise,
}


def reconstruct(
    sections: Dict[str, Section],
    format_style: str = "structured",
) -> str:
    """
    Reconstruct optimized prompt from classified sections.

    Args:
        sections: Compressed section dictionary.
        format_style: One of "structured", "xml", "natural", "concise".

    Returns:
        Fully reconstructed, optimized prompt string.
    """
    if not sections:
        return ""

    if format_style not in FORMATS:
        raise ValueError(
            f"Unknown format style '{format_style}'. "
            f"Choose from: {', '.join(FORMATS.keys())}"
        )

    result = FORMATS[format_style](sections)

    # Final cleanup
    result = re.sub(r'\n{3,}', '\n\n', result)
    result = re.sub(r'  +', ' ', result)

    return result.strip()
