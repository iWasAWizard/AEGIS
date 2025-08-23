# aegis/schemas/runtime.py
"""
Pydantic schema for defining runtime execution options for the agent system.

This module contains the `RuntimeExecutionConfig` model, which encapsulates
all user-configurable parameters that control the agent's behavior at
execution time. It is a data container; default values are populated by
the config_loader from config.yaml and presets.
"""

from typing import Optional, Literal, List

from pydantic import BaseModel, Field, field_validator


class RuntimeExecutionConfig(BaseModel):
    """
    Defines runtime options for a single task execution.
    All fields are optional, as they are merged from system defaults,
    presets, and launch-time overrides.
    """

    backend_profile: Optional[str] = Field(
        None,
        description="The name of the backend profile from backends.yaml to use for all backend services.",
    )
    llm_model_name: Optional[str] = Field(
        None,
        description="Abstract model name used to look up prompt formatters in aegis/models.yaml.",
    )
    llm_planning_timeout: Optional[int] = Field(
        None,
        description="Timeout in seconds for LLM planning queries.",
    )
    temperature: Optional[float] = Field(
        None,
        ge=0.0,
        le=2.0,
        description="LLM temperature (0.0-2.0). Lower is more deterministic.",
    )
    max_context_length: Optional[int] = Field(
        None,
        ge=256,
        description="Maximum context length (tokens) for the LLM.",
    )
    max_tokens_to_generate: Optional[int] = Field(
        None,
        ge=64,
        description="Maximum number of new tokens the LLM should generate per call.",
    )
    top_p: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Nucleus sampling parameter; considers tokens with cumulative probability up to this value.",
    )
    presence_penalty: Optional[float] = Field(
        None,
        ge=-2.0,
        le=2.0,
        description="Penalizes tokens based on whether they appear in the text so far.",
    )
    frequency_penalty: Optional[float] = Field(
        None,
        ge=-2.0,
        le=2.0,
        description="Penalizes tokens based on their frequency in the text so far.",
    )
    stop_sequences: Optional[List[str]] = Field(
        None, description="Stop generation when any of these strings is generated."
    )
    tool_timeout: Optional[int] = Field(
        None,
        description="Timeout in seconds for tool execution, unless a tool specifies its own.",
    )
    tool_retries: Optional[int] = Field(
        None,
        ge=0,
        description="Number of times to retry a failed tool execution.",
    )
    iterations: Optional[int] = Field(
        None,
        description="Maximum number of planning/execution steps before forced termination.",
    )
    tool_allowlist: List[str] = Field(
        default_factory=list,
        description="If provided, the agent will only be able to see and use tools from this list.",
    )
    tool_selection_threshold: Optional[int] = Field(
        None,
        description="If the number of available tools exceeds this many candidates, a preliminary LLM call is made to select a relevant subset.",
    )

    # --- runtime safety and determinism ---
    dry_run: Optional[bool] = Field(
        None,
        description="Force dry-run for side-effecting tools. Overrides env if set.",
    )
    seed: Optional[int] = Field(
        None,
        ge=0,
        description="Random seed for deterministic behavior where supported.",
    )
    wall_clock_timeout_s: Optional[int] = Field(
        None,
        description="Hard wall-clock timeout (seconds) for the entire task.",
    )

    class Config:
        extra = "ignore"
        populate_by_name = True

    @field_validator("temperature", mode="before")
    @classmethod
    def clamp_temperature(cls, v: float | None) -> float | None:
        if v is None:
            return v
        if v < 0.0:
            return 0.0
        if v > 2.0:
            return 2.0
        return v

    @field_validator("max_context_length", "max_tokens_to_generate", mode="before")
    @classmethod
    def check_positive_int(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError("Must be a positive integer.")
        return v

    @field_validator("top_p", mode="before")
    @classmethod
    def clamp_top_p(cls, v: float | None) -> float | None:
        if v is None:
            return v
        if v < 0.0:
            return 0.0
        if v > 1.0:
            return 1.0
        return v

    @field_validator("tool_timeout", "llm_planning_timeout", mode="before")
    @classmethod
    def check_positive_timeout(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError("Timeout must be a positive integer.")
        return v

    @field_validator("tool_retries", mode="before")
    @classmethod
    def check_nonnegative_retries(cls, v: int | None) -> int | None:
        if v is not None and v < 0:
            raise ValueError("Retries must be a non-negative integer.")
        return v

    @field_validator("iterations", mode="before")
    @classmethod
    def check_positive_iterations(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError("Iterations must be a positive integer.")
        return v

    @field_validator("tool_selection_threshold", mode="before")
    @classmethod
    def check_positive_threshold(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError("Tool selection threshold must be a positive integer.")
        return v
