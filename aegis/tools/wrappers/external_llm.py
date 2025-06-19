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

import openai  # type: ignore
import requests
from pydantic import BaseModel, Field

# Import ToolExecutionError
from aegis.exceptions import ToolExecutionError, ConfigurationError
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
    temperature: Optional[float] = Field(0.7, description="The sampling temperature.")
    timeout: Optional[int] = Field(
        60, description="The timeout in seconds for the API call."
    )


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
    :raises ToolExecutionError: If the OpenAI API call fails.
    """
    logger.info(f"Initiating OpenAI chat with model: {input_data.model}")
    try:
        # Ensure OPENAI_API_KEY is available either via input or environment
        api_key_to_use = input_data.api_key or os.getenv("OPENAI_API_KEY")
        if not api_key_to_use:
            raise ConfigurationError(
                "OpenAI API key not provided or found in environment (OPENAI_API_KEY)."
            )

        client = openai.OpenAI(api_key=api_key_to_use)  # type: ignore

        response = client.chat.completions.create(
            model=input_data.model,
            messages=[m.model_dump() for m in input_data.messages],  # type: ignore
            temperature=input_data.temperature,
            timeout=input_data.timeout,
        )
        content = response.choices[0].message.content
        return content or "[No content in OpenAI response]"
    except openai.APIError as e:  # Catch specific OpenAI errors
        logger.exception(f"OpenAI API error for model {input_data.model}: {e}")
        raise ToolExecutionError(f"OpenAI API error: {e}")
    except ConfigurationError:  # Re-raise our config error
        raise
    except Exception as e:  # Catch other unexpected errors (network, etc.)
        logger.exception(f"OpenAI chat completion failed for model {input_data.model}")
        raise ToolExecutionError(f"OpenAI chat completion failed: {e}")


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
    :raises ToolExecutionError: If the request to Ollama fails.
    """
    logger.info(
        f"Sending direct prompt to Ollama model: {input_data.model} via URL: {OLLAMA_DIRECT_API_URL}"
    )
    if not OLLAMA_DIRECT_API_URL:
        raise ConfigurationError(
            "OLLAMA_DIRECT_API_URL is not configured for ollama_generate_direct tool."
        )

    try:
        payload = {
            "model": input_data.model,
            "prompt": input_data.prompt,
            "stream": False,
        }
        if input_data.system is not None:
            payload["system"] = input_data.system
        if input_data.temperature is not None:
            payload["temperature"] = input_data.temperature

        options_payload = {}
        if (
            input_data.temperature is not None
        ):  # Ollama takes temperature in options for /api/generate
            options_payload["temperature"] = input_data.temperature
        # Add other common Ollama options if they were part of your input schema and needed
        # For now, keeping it minimal to what was in the original schema.
        if options_payload:
            payload["options"] = options_payload

        response = requests.post(
            OLLAMA_DIRECT_API_URL,
            json=payload,
            timeout=input_data.timeout or 60,  # Ensure timeout has a default
        )
        response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)

        response_json = response.json()
        generated_text = response_json.get("response")
        if (
            generated_text is None
        ):  # Check for None specifically, as empty string might be valid
            # Ollama sometimes puts error messages in the response field on non-200 or other issues
            if "error" in response_json:
                raise ToolExecutionError(
                    f"Ollama returned an error: {response_json['error']}"
                )
            raise ToolExecutionError(
                "Ollama response missing 'response' field or it is null."
            )

        return generated_text

    except requests.exceptions.RequestException as e:
        logger.exception(
            f"Direct Ollama generation request failed to {OLLAMA_DIRECT_API_URL}"
        )
        raise ToolExecutionError(f"Ollama request failed: {e}")
    except ConfigurationError:
        raise
    except Exception as e:  # Catch other unexpected errors
        logger.exception(
            f"Unexpected error in ollama_generate_direct to {OLLAMA_DIRECT_API_URL}"
        )
        raise ToolExecutionError(f"Unexpected error in ollama_generate_direct: {e}")
