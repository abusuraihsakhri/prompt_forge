import pytest
from promptforge.core.pipeline import optimize

def test_end_to_end_claude():
    raw = "Hey Claude, could you please write a Python function? Make sure to use recursion. Thanks!"
    res = optimize(raw, model="claude")
    
    assert "Task:" in res.optimized or "<task>" in res.optimized
    assert "Hey" not in res.optimized
    assert "Thanks" not in res.optimized
    assert "use recursion" in res.optimized
    assert res.savings_percent > 0

def test_end_to_end_gemini():
    raw = "Please write a python script. In order to do this well, make sure to use asyncio."
    res = optimize(raw, model="gemini")
    
    assert "→" in res.optimized or "•" in res.optimized
    assert "Please" not in res.optimized
    assert "In order to" not in res.optimized
    assert res.savings_percent > 0

def test_short_prompt():
    raw = "Write python."
    res = optimize(raw, model="chatgpt")
    # Should not break
    assert "Write python" in res.optimized
    assert res.savings_percent == 0.0
