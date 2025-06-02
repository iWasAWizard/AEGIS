"""
LLM wrapper tools for orchestrating language model queries and structured outputs.

Wraps LLM interfaces to support structured prompt chaining, tool planning, and output validation.
"""

from typing import List, Optional, Literal

import openai
import requests
from pydantic import BaseModel, Field

from aegis.registry import register_tool
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


class LLMGenerateInput(BaseModel):
    """
    LLMGenerateInput class.
    """

    prompt: str = Field(description="The raw prompt to complete.")
    model: str = Field(
        default="text-davinci-003", description="OpenAI completion model."
    )
    temperature: float = Field(default=0.7, description="Sampling temperature.")
    max_tokens: Optional[int] = Field(
        default=256, description="Max tokens to generate."
    )
    api_key: Optional[str] = Field(
        default=None, description="Optional override for OpenAI API key."
    )


class ChatMessage(BaseModel):
    """
    ChatMessage class.
    """

    role: Literal["system", "user", "assistant"]
    content: str


class LLMChatInput(BaseModel):
    """
    LLMChatInput class.
    """

    messages: List[ChatMessage]
    model: str = Field(default="gpt-4", description="LLM model to use.")
    temperature: float = Field(default=0.7, description="Sampling temperature.")
    api_key: Optional[str] = Field(
        default=None, description="Optional override for OpenAI API key."
    )


class OllamaGenerateInput(BaseModel):
    """
    OllamaGenerateInput class.
    """

    model: str = Field(description="Ollama model name (e.g. 'mistral', 'codellama').")
    prompt: str = Field(description="Prompt to send to the model.")
    system: Optional[str] = Field(
        default="", description="Optional system-level context."
    )
    temperature: Optional[float] = Field(default=0.7)


@register_tool(
    name="llm_generate",
    category="llm",
    input_model=LLMGenerateInput,
    tags=["llm", "generate", "openai", "wrapper"],
    description="Perform a raw text completion using an OpenAI model (non-chat).",
    safe_mode=True,
    purpose="Generate single-shot completions from a raw prompt using OpenAI's completion endpoint.",
)
def llm_generate(input_data: LLMGenerateInput) -> str:
    """
    llm_generate.
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    logger.info(f"Generating text with model {input_data.model}")
    client = openai.OpenAI(api_key=input_data.api_key) if input_data.api_key else openai
    try:
        response = client.completions.create(
            model=input_data.model,
            prompt=input_data.prompt,
            temperature=input_data.temperature,
            max_tokens=input_data.max_tokens,
        )
        return response.choices[0].text.strip()
    except Exception as e:
        logger.exception(f"[llm] Error: {e}")
        return f"[ERROR] Completion failed: {str(e)}"


@register_tool(
    name="llm_chat",
    input_model=LLMChatInput,
    tags=["llm", "chat", "wrapper"],
    description="Conduct a multi-turn conversation with an LLM using the OpenAI client interface.",
    safe_mode=True,
    purpose="Run a full chat prompt and get a single assistant response using OpenAI models.",
    category="llm",
)
def llm_chat(input_data: LLMChatInput) -> str:
    """
    llm_chat.
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    logger.info(f"Initiating LLM chat with model {input_data.model}")
    client = openai.OpenAI(api_key=input_data.api_key) if input_data.api_key else openai
    try:
        response = client.chat.completions.create(
            model=input_data.model,
            messages=[m.dict() for m in input_data.messages],
            temperature=input_data.temperature,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.exception(f"[llm] Error: {e}")
        return f"[ERROR] Chat completion failed: {str(e)}"


@register_tool(
    name="ollama_generate",
    input_model=OllamaGenerateInput,
    tags=["llm", "ollama", "wrapper"],
    description="Send a prompt to a local Ollama model for generation.",
    safe_mode=True,
    purpose="Run LLM completions using Ollama backend.",
    category="llm",
)
def ollama_generate(input_data: OllamaGenerateInput) -> str:
    """
    ollama_generate.
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    logger.info(f"Sending prompt to Ollama model {input_data.model}")
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": input_data.model,
            "prompt": input_data.prompt,
            "system": input_data.system,
            "temperature": input_data.temperature,
        },
    )
    return response.json()["response"]
