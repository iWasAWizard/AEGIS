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

    assert config.backend_profile is None
    assert config.llm_model_name is None
    assert config.safe_mode is None
    assert config.tool_timeout is None
    assert config.tool_retries is None
    assert config.iterations is None
    assert config.tool_allowlist == []


def test_runtime_config_valid_overrides():
    """Verify that valid values can be used to override the defaults."""
    config = RuntimeExecutionConfig(
        backend_profile="test_backend",
        llm_model_name="test_model",
        safe_mode=False,
        tool_timeout=60,
        tool_retries=3,
        iterations=100,
    )

    assert config.backend_profile == "test_backend"
    assert config.llm_model_name == "test_model"
    assert config.safe_mode is False
    assert config.tool_timeout == 60
    assert config.tool_retries == 3
    assert config.iterations == 100


@pytest.mark.parametrize(
    "field, invalid_value, expected_error_msg",
    [
        ("tool_timeout", 0, "Timeout must be a positive integer."),
        ("tool_timeout", -10, "Timeout must be a positive integer."),
        ("tool_retries", -1, "Retries must be a non-negative integer."),
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
