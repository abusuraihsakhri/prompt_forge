import pytest
from promptforge.core.parser import Section
from promptforge.core.reconstructor import reconstruct

@pytest.fixture
def sections():
    return {
        "task": Section("task", "write a python script"),
        "constraints": Section("constraints", "use recursion. avoid global variables"),
        "format": Section("format", "JSON")
    }

def test_reconstruct_structured(sections):
    res = reconstruct(sections, format_style="structured")
    assert "Task: write a python script" in res
    assert "Constraints:\n- use recursion" in res
    assert "- avoid global variables" in res
    assert "Output Format: JSON" in res

def test_reconstruct_xml(sections):
    res = reconstruct(sections, format_style="xml")
    assert "<task>write a python script</task>" in res
    assert "<constraints>\n - use recursion" in res
    assert "<output_format>JSON</output_format>" in res

def test_reconstruct_natural(sections):
    res = reconstruct(sections, format_style="natural")
    assert res.startswith("write a python script")
    assert "Requirements:\n- use recursion" in res
    assert "Output: JSON" in res

def test_reconstruct_concise(sections):
    res = reconstruct(sections, format_style="concise")
    assert "→ write a python script" in res
    assert "• use recursion" in res
    assert "Output: JSON" in res
