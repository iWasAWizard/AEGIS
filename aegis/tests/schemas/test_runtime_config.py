# aegis/tests/schemas/test_runtime_config.py
"""
Unit tests for the RuntimeExecutionConfig schema.
"""
import pytest
from pydantic import ValidationError

from aegis.schemas.runtime import RuntimeExecutionConfig


def test_runtime_config_defaults():
    """Verify that the default values are set correctly when no arguments are provided."""
    config = RuntimeExecutionConfig()

    assert config.model == "llama3"
    assert config.koboldcpp_url == "http://koboldcpp:5001/api/generate"
    assert config.safe_mode is True
    assert config.timeout == 30
    assert config.retries == 0
    assert config.iterations == 10


def test_runtime_config_valid_overrides():
    """Verify that valid values can be used to override the defaults."""
    config = RuntimeExecutionConfig(
        model="test_model", safe_mode=False, timeout=60, retries=3, iterations=100
    )

    assert config.model == "test_model"
    assert config.safe_mode is False
    assert config.timeout == 60
    assert config.retries == 3
    assert config.iterations == 100


@pytest.mark.parametrize(
    "field, invalid_value, expected_error_msg",
    [
        ("timeout", 0, "Timeout must be a positive integer."),
        ("timeout", -10, "Timeout must be a positive integer."),
        ("retries", -1, "Retries must be a non-negative integer."),
        ("iterations", 0, "Iterations must be a positive integer."),
        ("iterations", -5, "Iterations must be a positive integer."),
    ],
)
def test_runtime_config_invalid_values(field, invalid_value, expected_error_msg):
    """Test that field validators raise ValidationErrors for invalid numeric inputs."""
    invalid_data = {field: invalid_value}

    with pytest.raises(ValidationError) as exc_info:
        RuntimeExecutionConfig(**invalid_data)

    # Check if the specific error message from our validator is in the Pydantic error details
    assert expected_error_msg in str(exc_info.value)
