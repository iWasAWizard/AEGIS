# aegis/tools/wrappers/external_llm.py
"""
Wrapper tools for interacting with external, third-party language models.

This module provides tools for connecting to commercial LLM APIs like OpenAI, or
for making direct, low-level calls to a local Ollama instance. It is distinct
from the internal `llm_query` utility, which is designed for the primary,
local agent planner. These tools allow the agent to leverage other models for
specific tasks where a different capability is desired.
"""
import os
from typing import List, Optional, Literal

import openai
import requests  # Restored
from pydantic import BaseModel, Field

from aegis.registry import register_tool
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)

# Specific URL for the ollama_generate_direct tool
OLLAMA_DIRECT_API_URL = os.getenv(
    "OLLAMA_DIRECT_API_URL", "http://localhost:11434/api/generate"
)


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
    :ivar timeout: The timeout in seconds for the API call.
    :vartype timeout: Optional[int]
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
    timeout: Optional[int] = Field(
        60, description="The timeout in seconds for the API call."
    )
    api_key: Optional[str] = Field(
        None, description="Optional override for the OpenAI API key."
    )


# --- Restored OllamaGenerateInput and ollama_generate_direct tool ---
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
    :ivar timeout: The timeout in seconds for the API call.
    :vartype timeout: Optional[int]
    """

    model: str = Field(
        ...,
        description="The name of the Ollama model to use (e.g., 'mistral', 'codellama').",
    )
    prompt: str = Field(..., description="The prompt to send to the model.")
    system: Optional[str] = Field(
        None, description="An optional system-level context string."
    )
    temperature: Optional[float] = Field(
        0.7, description="The sampling temperature."
    )  # Default for Ollama
    timeout: Optional[int] = Field(
        60, description="The timeout in seconds for the API call."
    )


# --- End of restored OllamaGenerateInput ---


@register_tool(
    name="llm_chat_openai",
    input_model=LLMChatInput,
    tags=["llm", "chat", "openai", "wrapper", "external"],
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
        client = (
            openai.OpenAI(api_key=input_data.api_key)
            if input_data.api_key
            else openai.OpenAI()
        )
        response = client.chat.completions.create(
            model=input_data.model,
            messages=[m.model_dump() for m in input_data.messages],
            temperature=input_data.temperature,
            timeout=input_data.timeout,
        )
        return response.choices[0].message.content or "[No content in response]"
    except Exception as e:
        logger.exception(f"OpenAI chat completion failed for model {input_data.model}")
        return f"[ERROR] OpenAI chat completion failed: {e}"


# --- Restored ollama_generate_direct tool ---
@register_tool(
    name="ollama_generate_direct",
    input_model=OllamaGenerateInput,
    tags=["llm", "ollama", "wrapper", "external"],
    description="Sends a raw prompt to a local Ollama model for generation. Uses OLLAMA_DIRECT_API_URL.",
    safe_mode=True,
    purpose="Run a simple, single-shot completion using a specific Ollama model.",
    category="llm",
)
def ollama_generate_direct(input_data: OllamaGenerateInput) -> str:
    """Sends a direct, single-prompt request to a local Ollama instance.

    Note: This is a lower-level tool than the main `llm_query` utility and does
    not use the advanced chat templating. It is useful for simple, one-off
    generations where a specific model or raw prompt is required.
    It uses the OLLAMA_DIRECT_API_URL environment variable or defaults to 'http://localhost:11434/api/generate'.

    :param input_data: An object containing the model, prompt, and system context.
    :type input_data: OllamaGenerateInput
    :return: The generated text response from the Ollama model.
    :rtype: str
    """
    logger.info(
        f"Sending direct prompt to Ollama model: {input_data.model} via URL: {OLLAMA_DIRECT_API_URL}"
    )
    try:
        payload = {
            "model": input_data.model,
            "prompt": input_data.prompt,
            "stream": False,  # Explicitly false for non-streaming
        }
        # Add optional parameters if they are provided
        if input_data.system is not None:
            payload["system"] = input_data.system
        if (
            input_data.temperature is not None
        ):  # Ollama /generate takes temp directly, not in options
            payload["temperature"] = input_data.temperature
        # Other Ollama options like num_ctx, top_k, top_p would go into an "options" dict if needed
        # For this simple tool, we keep it minimal.

        response = requests.post(
            OLLAMA_DIRECT_API_URL,
            json=payload,
            timeout=input_data.timeout,
        )
        response.raise_for_status()
        # Ollama's direct /generate response format
        return response.json().get("response", "[No response field in result]")
    except requests.RequestException as e:
        logger.exception(
            f"Direct Ollama generation request failed to {OLLAMA_DIRECT_API_URL}"
        )
        return f"[ERROR] Ollama request failed: {e}"


# --- End of restored ollama_generate_direct tool ---
