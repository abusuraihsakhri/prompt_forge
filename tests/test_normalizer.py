import pytest
from promptforge.core.normalizer import (
    normalize, collapse_whitespace, remove_fillers, fix_punctuation, Aggressiveness
)

def test_collapse_whitespace():
    # Test spaces
    assert collapse_whitespace("hello    world") == "hello world"
    # Test blank lines
    assert collapse_whitespace("hello\n\n\n\nworld") == "hello\n\nworld"
    # Test trailing
    assert collapse_whitespace("hello \n world ") == "hello\n world"

def test_remove_fillers_conservative():
    text = "Hey Claude, please help me with this. Thanks!"
    result = remove_fillers(text, Aggressiveness.CONSERVATIVE)
    assert "Hey" not in result
    assert "please" not in result
    assert "Thanks" not in result

def test_remove_fillers_aggressive():
    text = "I just basically want you to really just do this."
    result = remove_fillers(text, Aggressiveness.AGGRESSIVE)
    assert "just" not in result.lower()
    assert "basically" not in result.lower()
    assert "really" not in result.lower()

def test_word_boundaries():
    text = "The thematic presentation was essentially literal please."
    # 'basically' should match, but 'thematic' (contains 'thematic') shouldn't match a bad regex
    # 'literal' should not match 'literally'
    result = remove_fillers(text, Aggressiveness.AGGRESSIVE)
    assert "thematic" in result
    assert "literal" in result
    assert "essentially" not in result
    assert "please" not in result

def test_fix_punctuation():
    # Double spaces
    assert fix_punctuation("hello  world") == "Hello world"
    # Space before punctuation
    assert fix_punctuation("hello , world !") == "Hello, world!"
    # Double punctuation
    assert fix_punctuation("hello,, world!!") == "Hello, world!"
    # Capitalization
    assert fix_punctuation("hello. world") == "Hello. World"

def test_full_normalize():
    raw = "Hey Claude, could you please basically \n\n\n   just write a python script? Thanks!"
    res = normalize(raw, aggressiveness=Aggressiveness.AGGRESSIVE)
    assert res == "Claude, write a python script?"
