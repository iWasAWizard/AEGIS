# aegis/schemas/runtime.py
"""
Pydantic schema for defining runtime execution options for the agent system.

This module contains the `RuntimeExecutionConfig` model, which encapsulates
all user-configurable parameters that control the agent's behavior at
execution time. It is a data container; default values are populated by
the config_loader from config.yaml and presets.
"""

from typing import Optional, Literal

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
        description="Nucleus sampling (top-p) parameter.",
    )
    top_k: Optional[int] = Field(
        None,
        ge=0,
        description="Top-k sampling parameter.",
    )
    repetition_penalty: Optional[float] = Field(
        None,
        ge=1.0,
        description="Repetition penalty for LLM generation (typically >1.0).",
    )
    safe_mode: Optional[bool] = Field(
        None,
        description="Whether to restrict execution to tools marked safe_mode=True.",
    )
    tool_timeout: Optional[int] = Field(
        None,
        description="Maximum runtime (in seconds) before aborting a tool execution.",
    )
    tool_retries: Optional[int] = Field(
        None,
        description="Number of times to retry a failed tool execution.",
    )
    iterations: Optional[int] = Field(
        None,
        description="Maximum number of planning/execution steps before forced termination.",
    )

    class Config:
        extra = "forbid"

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
