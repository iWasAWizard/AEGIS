# aegis/tools/wrappers/llm.py
"""
LLM wrapper tools for interacting with external, third-party language models.

This module provides tools for connecting to commercial LLM APIs like OpenAI.
It is distinct from the internal `llm_query` utility, which is designed for
the primary, local Ollama-based agent planner. These tools allow the agent
to leverage other models for specific tasks.
"""

from typing import List, Optional, Literal

import openai
import requests
from pydantic import BaseModel, Field

from aegis.registry import register_tool
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


class ChatMessage(BaseModel):
    """A single message in a chat conversation, conforming to OpenAI's schema.

    :ivar role: The role of the message author ("system", "user", or "assistant").
    :vartype role: Literal["system", "user", "assistant"]
    :ivar content: The content of the message.
    :vartype content: str
    """

    role: Literal["system", "user", "assistant"] = Field(
        ..., description="The role of the message author."
    )
    content: str = Field(..., description="The content of the message.")


class LLMChatInput(BaseModel):
    """Input for conducting a multi-turn conversation with an OpenAI-compatible chat model.

    :ivar messages: A list of messages forming the conversation history.
    :vartype messages: List[ChatMessage]
    :ivar model: The chat model to use (e.g., 'gpt-4', 'gpt-3.5-turbo').
    :vartype model: str
    :ivar temperature: The sampling temperature for the model.
    :vartype temperature: float
    :ivar api_key: Optional override for the OpenAI API key. If not provided,
                   the `OPENAI_API_KEY` environment variable is used.
    :vartype api_key: Optional[str]
    """

    messages: List[ChatMessage] = Field(
        ..., description="A list of messages forming the conversation history."
    )
    model: str = Field(
        "gpt-4", description="The chat model to use (e.g., 'gpt-4', 'gpt-3.5-turbo')."
    )
    temperature: float = Field(
        0.7, ge=0.0, le=2.0, description="The sampling temperature for the model."
    )
    api_key: Optional[str] = Field(
        None, description="Optional override for the OpenAI API key."
    )


class OllamaGenerateInput(BaseModel):
    """Input for generating text with a local Ollama model via a direct request.

    :ivar model: The name of the Ollama model to use (e.g., 'mistral', 'codellama').
    :vartype model: str
    :ivar prompt: The prompt to send to the model.
    :vartype prompt: str
    :ivar system: An optional system-level context string.
    :vartype system: Optional[str]
    :ivar temperature: The sampling temperature.
    :vartype temperature: Optional[float]
    """

    model: str = Field(
        ...,
        description="The name of the Ollama model to use (e.g., 'mistral', 'codellama').",
    )
    prompt: str = Field(..., description="The prompt to send to the model.")
    system: Optional[str] = Field(
        None, description="An optional system-level context string."
    )
    temperature: Optional[float] = Field(0.7, description="The sampling temperature.")


@register_tool(
    name="llm_chat_openai",
    input_model=LLMChatInput,
    tags=["llm", "chat", "openai", "wrapper"],
    description="Conducts a multi-turn conversation with an OpenAI chat model.",
    safe_mode=True,
    purpose="Leverage an external OpenAI model for a specific conversational task.",
    category="llm",
)
def llm_chat_openai(input_data: LLMChatInput) -> str:
    """Sends a chat history to an OpenAI model and returns the assistant's response.

    :param input_data: An object containing the message history, model, and other parameters.
    :type input_data: LLMChatInput
    :return: The content of the assistant's response message.
    :rtype: str
    """
    logger.info(f"Initiating OpenAI chat with model: {input_data.model}")
    try:
        # Use the provided API key if available, otherwise rely on environment variables.
        client = (
            openai.OpenAI(api_key=input_data.api_key) if input_data.api_key else openai
        )

        response = client.chat.completions.create(
            model=input_data.model,
            messages=[m.model_dump() for m in input_data.messages],
            temperature=input_data.temperature,
        )
        return response.choices[0].message.content or "[No content in response]"
    except Exception as e:
        logger.exception(f"OpenAI chat completion failed for model {input_data.model}")
        return f"[ERROR] OpenAI chat completion failed: {e}"


@register_tool(
    name="ollama_generate_direct",
    input_model=OllamaGenerateInput,
    tags=["llm", "ollama", "wrapper"],
    description="Sends a raw prompt to a local Ollama model for generation.",
    safe_mode=True,
    purpose="Run a simple, single-shot completion using a specific Ollama model.",
    category="llm",
)
def ollama_generate_direct(input_data: OllamaGenerateInput) -> str:
    """Sends a direct, single-prompt request to a local Ollama instance.

    Note: This is a lower-level tool than the main `llm_query` utility and does
    not use the advanced chat templating. It is useful for simple, one-off
    generations where a specific model or raw prompt is required.

    :param input_data: An object containing the model, prompt, and system context.
    :type input_data: OllamaGenerateInput
    :return: The generated text response from the Ollama model.
    :rtype: str
    """
    logger.info(f"Sending direct prompt to Ollama model: {input_data.model}")
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": input_data.model,
                "prompt": input_data.prompt,
                "system": input_data.system,
                "temperature": input_data.temperature,
                "stream": False,
            },
            timeout=60,
        )
        response.raise_for_status()
        return response.json().get("response", "[No response field in result]")
    except requests.RequestException as e:
        logger.exception("Direct Ollama generation request failed")
        return f"[ERROR] Ollama request failed: {e}"
