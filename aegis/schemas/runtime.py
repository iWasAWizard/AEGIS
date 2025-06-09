# aegis/schemas/runtime.py
"""
Pydantic schema for defining runtime execution options for the agent system.

This module contains the `RuntimeExecutionConfig` model, which encapsulates
all user-configurable parameters that control the agent's behavior at
execution time, such as model selection, safety constraints, and operational
limits like timeouts and retries.
"""

from pydantic import BaseModel, Field, field_validator


class RuntimeExecutionConfig(BaseModel):
    """Defines supported runtime options for a single task execution.

    This model includes parameters for the LLM backend, timeout/retry behavior,
    iteration limits, and safety constraints. It can be defined in a preset
    or overridden at launch time.

    :ivar model: The name of the LLM to use for task execution.
    :vartype model: str
    :ivar ollama_url: The URL of the Ollama-compatible inference endpoint.
    :vartype ollama_url: str
    :ivar safe_mode: If True, restricts execution to tools marked as safe.
    :vartype safe_mode: bool
    :ivar timeout: The default timeout in seconds for tool execution.
    :vartype timeout: int | None
    :ivar retries: The default number of times to retry a failed tool.
    :vartype retries: int | None
    :ivar iterations: The maximum number of planning/execution steps before forced termination.
    :vartype iterations: int | None
    """

    model: str = Field(
        default="llama3",
        description="Name of the LLM to use for task execution.",
    )

    ollama_url: str = Field(
        default="http://ollama:11434/api/generate",
        description="URL of the model backend or inference endpoint.",
    )

    safe_mode: bool = Field(
        default=True,
        description="Whether to restrict execution to tools marked safe_mode=True.",
    )

    timeout: int | None = Field(
        default=30,
        description="Maximum runtime (in seconds) before aborting a tool execution.",
    )

    retries: int | None = Field(
        default=0,
        description="Number of times to retry a failed tool execution.",
    )

    iterations: int | None = Field(
        default=10,
        description="Maximum number of planning/execution steps before forced termination.",
    )

    class Config:
        """Pydantic model configuration."""

        extra = "forbid"

    @field_validator("timeout", mode="before")
    def check_positive_timeout(cls, v: int | None) -> int | None:
        """Ensures the timeout, if provided, is a positive integer."""
        if v is not None and v <= 0:
            raise ValueError("Timeout must be a positive integer.")
        return v

    @field_validator("retries", mode="before")
    def check_nonnegative_retries(cls, v: int | None) -> int | None:
        """Ensures the retry count, if provided, is not negative."""
        if v is not None and v < 0:
            raise ValueError("Retries must be a non-negative integer.")
        return v

    @field_validator("iterations", mode="before")
    def check_positive_iterations(cls, v: int | None) -> int | None:
        """Ensures the iteration limit, if provided, is a positive integer."""
        if v is not None and v <= 0:
            raise ValueError("Iterations must be a positive integer.")
        return v
