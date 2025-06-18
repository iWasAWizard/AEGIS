# aegis/schemas/runtime.py
"""
Pydantic schema for defining runtime execution options for the agent system.

This module contains the `RuntimeExecutionConfig` model, which encapsulates
all user-configurable parameters that control the agent's behavior at
execution time, such as model selection, safety constraints, and operational
limits like timeouts and retries.
"""

from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator


class RuntimeExecutionConfig(BaseModel):
    """Defines supported runtime options for a single task execution.

    This model includes parameters for the LLM backend, timeout/retry behavior,
    iteration limits, and safety constraints. It can be defined in a preset
    or overridden at launch time.

    :ivar llm_backend_type: Specifies which LLM backend to use ('ollama' or 'koboldcpp'). Defaults to 'ollama'.
    :vartype llm_backend_type: Literal["ollama", "koboldcpp"]
    :ivar llm_model_name: The name/identifier of the LLM model to use (e.g., 'llama3' for Ollama).
                         If None, uses OLLAMA_MODEL or KOBOLDCPP_MODEL env var based on backend_type.
    :vartype llm_model_name: Optional[str]
    :ivar ollama_api_url: The URL of the Ollama inference endpoint.
    :vartype ollama_api_url: str
    :ivar koboldcpp_api_url: The URL of the KoboldCPP inference endpoint.
    :vartype koboldcpp_api_url: Optional[str]
    :ivar llm_planning_timeout: The timeout in seconds for LLM planning queries.
    :vartype llm_planning_timeout: int
    :ivar temperature: The sampling temperature for the LLM (0.0-2.0). Lower is more deterministic.
    :vartype temperature: float
    :ivar max_context_length: The maximum context length (tokens) the model can handle.
    :vartype max_context_length: int
    :ivar max_tokens_to_generate: The maximum number of new tokens the LLM should generate.
    :vartype max_tokens_to_generate: int
    :ivar top_p: Nucleus sampling parameter.
    :vartype top_p: Optional[float]
    :ivar top_k: Top-k sampling parameter.
    :vartype top_k: Optional[int]
    :ivar repetition_penalty: Repetition penalty for LLM generation.
    :vartype repetition_penalty: Optional[float]
    :ivar safe_mode: If True, restricts execution to tools marked as safe.
    :vartype safe_mode: bool
    :ivar tool_timeout: The default timeout in seconds for tool execution.
    :vartype tool_timeout: int | None
    :ivar tool_retries: The default number of times to retry a failed tool.
    :vartype tool_retries: int | None
    :ivar iterations: The maximum number of planning/execution steps before forced termination.
    :vartype iterations: int | None
    """

    llm_backend_type: Literal["ollama", "koboldcpp"] = Field(
        default="ollama",
        description="Specifies which LLM backend to use ('ollama' or 'koboldcpp').",
    )
    llm_model_name: Optional[str] = Field(
        default=None,
        description="Name/identifier of the LLM model. If None, uses OLLAMA_MODEL or KOBOLDCPP_MODEL (based on backend_type) env var.",
    )
    ollama_api_url: str = Field(  # Made non-optional again for default Ollama backend
        default="http://ollama:11434/api/generate",
        description="URL of the Ollama inference endpoint.",
    )
    koboldcpp_api_url: Optional[str] = Field(
        default=None,
        description="URL of the KoboldCPP inference endpoint (e.g., 'http://koboldcpp:5001/api/v1/generate'). Set if using 'koboldcpp' backend.",
    )
    llm_planning_timeout: int = Field(
        default=300,
        description="Timeout in seconds for LLM planning queries.",
    )
    temperature: float = Field(
        default=0.2,
        ge=0.0,
        le=2.0,
        description="LLM temperature (0.0-2.0). Lower is more deterministic.",
    )
    max_context_length: int = Field(
        default=4096,
        ge=256,
        description="Maximum context length (tokens) for the LLM.",
    )
    max_tokens_to_generate: int = Field(
        default=1536,
        ge=64,
        description="Maximum number of new tokens the LLM should generate per call.",
    )
    top_p: Optional[float] = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Nucleus sampling (top-p) parameter.",
    )
    top_k: Optional[int] = Field(
        default=40,
        ge=0,
        description="Top-k sampling parameter.",
    )
    repetition_penalty: Optional[float] = Field(
        default=1.1,
        ge=1.0,
        description="Repetition penalty for LLM generation (typically >1.0).",
    )
    safe_mode: bool = Field(
        default=True,
        description="Whether to restrict execution to tools marked safe_mode=True.",
    )
    tool_timeout: int | None = Field(
        default=60,
        description="Maximum runtime (in seconds) before aborting a tool execution.",
    )
    tool_retries: int | None = Field(
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

    @field_validator("tool_timeout", "llm_planning_timeout", mode="before")
    @classmethod
    def check_positive_timeout(cls, v: int | None) -> int | None:
        """Ensures the timeout, if provided, is a positive integer."""
        if v is not None and v <= 0:
            raise ValueError("Timeout must be a positive integer.")
        return v

    @field_validator("tool_retries", mode="before")
    @classmethod
    def check_nonnegative_retries(cls, v: int | None) -> int | None:
        """Ensures the retry count, if provided, is not negative."""
        if v is not None and v < 0:
            raise ValueError("Retries must be a non-negative integer.")
        return v

    @field_validator("iterations", mode="before")
    @classmethod
    def check_positive_iterations(cls, v: int | None) -> int | None:
        """Ensures the iteration limit, if provided, is a positive integer."""
        if v is not None and v <= 0:
            raise ValueError("Iterations must be a positive integer.")
        return v

    @field_validator("koboldcpp_api_url", "ollama_api_url", mode="before")
    @classmethod
    def check_url_format(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.startswith(("http://", "https://")):
            raise ValueError("API URL must start with http:// or https://")
        return v
