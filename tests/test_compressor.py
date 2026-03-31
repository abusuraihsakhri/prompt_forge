import pytest
from promptforge.core.parser import Section
from promptforge.core.compressor import compress_text, compress_sections

def test_apply_compression_rules():
    assert compress_text("make sure that you use python") == "ensure use python"
    assert compress_text("in order to win") == "to win"
    assert compress_text("due to the fact that it rained") == "because it rained"
    assert compress_text("prior to the start") == "before the start"

def test_deduplicate_constraints():
    # Two sentences saying the same thing shouldn't result in duplicates.
    text = "You must use Python to write the app. Ensure you use Python to write the app."
    # Because of overlap deduplication, the second one should be removed.
    res = compress_text(text)
    assert "You must use Python" in res
    assert "Ensure you use Python" not in res

def test_compress_sections():
    sections = {
        "task": Section("task", "write a python script"),
        "constraints": Section("constraints", "make sure that you use recursion")
    }
    comp = compress_sections(sections)
    assert comp["task"].content == "write a python script"
    assert comp["constraints"].content == "ensure use recursion"
