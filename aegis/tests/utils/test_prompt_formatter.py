# aegis/tests/utils/test_prompt_formatter.py
"""
Tests for the prompt formatting utility.
"""
from aegis.utils.prompt_formatter import format_prompt


def test_format_llama3():
    """Verify that the Llama 3 format is used for llama3 models."""
    messages = [{"role": "user", "content": "hello"}]
    result = format_prompt("llama3:8b-instruct", messages)
    assert result.startswith("<|begin_of_text|>")
    assert result.endswith("<|start_header_id|>assistant<|end_header_id|>\n\n")
    assert "<|start_header_id|>user<|end_header_id|>" in result


def test_format_mistral():
    """Verify that the ChatML format is used for mistral models."""
    messages = [{"role": "user", "content": "hello"}]
    result = format_prompt("mistral:7b-instruct-v0.2", messages)
    assert result.startswith("<|im_start|>")
    assert result.endswith("<|im_start|>assistant\n")


def test_format_gemma():
    """Verify that the ChatML format is used for gemma models."""
    messages = [{"role": "user", "content": "hello"}]
    result = format_prompt("gemma:7b", messages)
    assert result.startswith("<|im_start|>")
    assert result.endswith("<|im_start|>assistant\n")


def test_format_fallback_uses_chatml():
    """Verify that an unknown model name defaults to the ChatML format."""
    messages = [{"role": "user", "content": "hello"}]
    result = format_prompt("some-new-future-model:100b", messages)
    assert result.startswith("<|im_start|>")
    assert result.endswith("<|im_start|>assistant\n")


def test_format_is_case_insensitive():
    """Verify that model name matching is case-insensitive."""
    messages = [{"role": "user", "content": "hello"}]
    # Test with uppercase
    result = format_prompt("LLAMA3", messages)
    assert result.startswith("<|begin_of_text|>")
