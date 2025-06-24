# aegis/tools/wrappers/external_llm.py
"""
Wrapper tools for interacting with external, third-party language models.

This module provides tools for connecting to commercial LLM APIs like OpenAI.
It is distinct from the internal `llm_query` utility, which is designed for the primary,
local agent planner. These tools allow the agent to leverage other models for
specific tasks where a different capability is desired.
"""
import os
from typing import List, Optional, Literal

import openai  # type: ignore
from pydantic import BaseModel, Field

# Import ToolExecutionError
from aegis.exceptions import ToolExecutionError, ConfigurationError
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
