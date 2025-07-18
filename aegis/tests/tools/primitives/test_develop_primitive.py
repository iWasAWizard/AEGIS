# aegis/tests/tools/primitives/test_develop_primitive.py
"""
Unit tests for the development and testing primitive tools.
"""

from aegis.tools.primitives.develop import echo_input, EchoInputModel, no_op, NoOpModel


def test_echo_input():
    """Verify that the echo_input tool returns its payload unchanged."""
    payload = {"a": 1, "b": "test", "c": [1, 2]}
    input_data = EchoInputModel(payload=payload)
    result = echo_input(input_data)
    assert result == payload


def test_no_op():
    """Verify that the no_op tool returns the static 'ok' string."""
    input_data = NoOpModel()
    result = no_op(input_data)
    assert result == "ok"
