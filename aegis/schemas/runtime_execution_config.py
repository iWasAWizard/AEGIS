from pydantic import BaseModel, Field
from typing import Optional


class RuntimeExecutionConfig(BaseModel):
    """
    Configuration passed by the client to influence runtime behavior,
    without exposing internal agent graph wiring.
    """

    model: str = Field(
        default="hf.co/unsloth/granite-3.3-8b-instruct-GGUF:Q4_K_M",
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
