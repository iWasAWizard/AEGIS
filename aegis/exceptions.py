# aegis/exceptions.py
"""
Defines custom exception classes for the AEGIS framework.

Using custom exceptions allows for more precise error handling and clearer
distinction between different types of runtime failures, such as configuration
issues, tool execution problems, or LLM planning errors.
"""
from typing import Optional, Any


class AegisError(Exception):
    """Base exception class for all custom errors in the AEGIS application."""

    pass


class ConfigurationError(AegisError):
    """Raised when there is an error in loading or validating configuration.

    This can include a missing preset file, an unresolvable secret, or an
    invalid graph structure.
    """

    pass


class ToolError(AegisError):
    """Base exception for errors related to tool handling."""

    pass


class ToolNotFoundError(ToolError, KeyError):
    """Raised when a requested tool cannot be found in the registry.

    This typically occurs if the agent's plan references a tool that is not
    registered or has been misspelled. Inherits from `KeyError` for some
    backwards compatibility.
    """

    pass


class ToolExecutionError(ToolError):
    """Raised when a tool fails during its execution for reasons other than
    invalid input.

    This includes network errors, subprocess failures, timeouts, or any
    unhandled internal exception within the tool's logic.
    """

    pass


class ToolValidationError(ToolError, ValueError):
    """Raised when the input provided to a tool fails Pydantic validation.

    This error occurs before the tool is executed, indicating that the agent's
    plan provided arguments that do not match the tool's required input schema.
    Inherits from `ValueError` for some backwards compatibility.
    """

    pass


class PlannerError(AegisError):
    """Raised when the LLM planning phase fails.

    This can be due to the LLM returning unparsable JSON, a malformed plan
    that fails schema validation, or a network failure when communicating
    with the LLM service.
    """

    def __init__(
        self,
        message: str,
        raw_json_content: Optional[str] = None,
        validation_error: Optional[Any] = None,
    ):
        """Initializes the PlannerError with optional structured context."""
        super().__init__(message)
        self.raw_json_content = raw_json_content
        self.validation_error = validation_error
