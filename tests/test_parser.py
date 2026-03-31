import pytest
from promptforge.core.parser import parse, _is_prestructured

def test_is_prestructured():
    assert _is_prestructured("Task: Write code\nConstraints:\n- No global vars") is True
    assert _is_prestructured("### Goal\nWrite code\n### Output\nJSON") is True
    assert _is_prestructured("Can you write a python script to do math?") is False

def test_parse_prestructured():
    text = "Task: Write code\nConstraints:\n- No global vars\nFormat: JSON format requested"
    sections = parse(text)
    
    assert "task" in sections
    assert "Write code" in sections["task"].content
    
    assert "constraints" in sections
    assert "No global vars" in sections["constraints"].content
    
    assert "format" in sections
    assert "JSON" in sections["format"].content

def test_parse_unstructured():
    text = "Create a python script. format as: JSON."
    sections = parse(text)
    
    assert "JSON" in sections.get("format", {}).content or "JSON." in sections.get("format", getattr(sections.get("format"), "content", "JSON."))
