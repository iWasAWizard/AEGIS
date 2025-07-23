# aegis/schemas/backend.py
"""
Pydantic schemas for defining backend provider configurations.
"""
from typing import Literal, Optional

from pydantic import BaseModel, Field


class BaseBackendConfig(BaseModel):
    """Base model for all backend configurations."""

    profile_name: str = Field(..., description="Unique name for this backend profile.")
    type: str = Field(
        ..., description="The type of backend provider (e.g., 'koboldcpp', 'openai')."
    )


class KoboldcppBackendConfig(BaseBackendConfig):
    """Configuration specific to a KoboldCPP backend."""

    type: Literal["koboldcpp"] = "koboldcpp"
    llm_url: str = Field(
        ..., description="The full URL to the KoboldCPP /generate endpoint."
    )
    temperature: float = Field(0.2)
    max_tokens_to_generate: int = Field(1536)
    top_p: float = Field(0.9)
    top_k: int = Field(40)
    repetition_penalty: float = Field(1.1)


class BendBackendConfig(KoboldcppBackendConfig):
    """Configuration for a full BEND stack, extending KoboldCPP with other services."""

    type: Literal["bend"] = "bend"
    voice_proxy_url: Optional[str] = Field(
        None, description="URL for the BEND voice proxy service (TTS/STT)."
    )
    rag_url: Optional[str] = Field(
        None, description="URL for the BEND RAG retriever service."
    )
    api_key: Optional[str] = Field(
        None, description="API key for securing BEND services."
    )


class OllamaBackendConfig(BaseBackendConfig):
    """Configuration specific to an Ollama backend."""

    type: Literal["ollama"] = "ollama"
    llm_url: str = Field(
        ..., description="The full URL to the Ollama /api/generate endpoint."
    )
    temperature: float = Field(0.5)
    max_tokens_to_generate: int = Field(2048)
    top_p: float = Field(0.9)
    top_k: int = Field(40)
    repetition_penalty: float = Field(1.1)


class VllmBackendConfig(BaseBackendConfig):
    """Configuration specific to a vLLM OpenAI-compatible backend."""

    type: Literal["vllm"] = "vllm"
    llm_url: str = Field(
        ..., description="The full URL to the vLLM /v1/chat/completions endpoint."
    )
    model: str = Field(
        "aegis-agent-model",
        description="The served model name, as defined in the vLLM server command.",
    )
    temperature: float = Field(0.2)
    max_tokens_to_generate: int = Field(1536)
    top_p: float = Field(0.9)
    top_k: int = Field(-1)  # -1 is often used to disable top-k in vLLM
    repetition_penalty: float = Field(1.1)


class OpenAIBackendConfig(BaseModel):
    """Configuration specific to an OpenAI-compatible API backend."""

    profile_name: str = Field(..., description="Unique name for this backend profile.")
    type: Literal["openai"] = "openai"
    model: str = Field(
        default="gpt-4-turbo", description="The model name to use for completions."
    )
    api_key: str = Field(..., description="The API key for the OpenAI service.")
    temperature: float = Field(0.7)
    max_tokens_to_generate: int = Field(2048)
    top_p: float = Field(1.0)
    tts_model: str = Field(
        default="tts-1", description="The model name for text-to-speech."
    )
    tts_voice: Literal["alloy", "echo", "fable", "onyx", "nova", "shimmer"] = Field(
        default="alloy", description="The voice to use for text-to-speech."
    )
    stt_model: str = Field(
        default="whisper-1", description="The model name for speech-to-text."
    )


class BackendManifest(BaseModel):
    """Represents the entire collection of backends defined in backends.yaml."""

    backends: list[dict]
