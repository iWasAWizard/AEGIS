# aegis/utils/prompt_formatter.py
"""
Centralized prompt formatting utility to support multiple LLM chat templates.
"""
from typing import List, Dict, Any

from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


def _format_llama3(messages: List[Dict[str, Any]]) -> str:
    """Formats prompts using the Llama 3 instruction template."""
    prompt = "<|begin_of_text|>"
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        prompt += f"<|start_header_id|>{role}<|end_header_id|>\n\n{content}<|eot_id|>"
    # Add the prompt for the assistant's turn
    prompt += "<|start_header_id|>assistant<|end_header_id|>\n\n"
    return prompt


def _format_chatml(messages: List[Dict[str, Any]]) -> str:
    """Formats prompts using the ChatML template (used by Mistral, many others)."""
    prompt = ""
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        prompt += f"<|im_start|>{role}\n{content}<|im_end|>\n"
    # Add the prompt for the assistant's turn
    prompt += "<|im_start|>assistant\n"
    return prompt


def format_prompt(model_name: str, messages: List[Dict[str, Any]]) -> str:
    """
    Selects the appropriate prompt formatter based on the model name and formats
    the message history into a single string for the LLM.

    :param model_name: The name of the model being used (e.g., 'llama3', 'mistral').
    :param messages: A list of message dictionaries, each with a 'role' and 'content'.
    :return: A single, correctly formatted prompt string.
    """
    model_name_lower = model_name.lower()

    if "llama3" in model_name_lower:
        logger.debug(f"Using Llama 3 prompt format for model: {model_name}")
        return _format_llama3(messages)

    # ChatML is a very common format, especially for instruction-tuned models.
    if "mistral" in model_name_lower or "gemma" in model_name_lower:
        logger.debug(f"Using ChatML prompt format for model: {model_name}")
        return _format_chatml(messages)

    # Fallback for unknown models
    logger.warning(
        f"No specific prompt format found for '{model_name}'. Using generic ChatML as a fallback."
    )
    return _format_chatml(messages)
