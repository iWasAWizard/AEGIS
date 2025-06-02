"""
Utilities for formatting prompts and retrieving model configuration.
"""

import requests

from aegis.utils.logger import setup_logger
from aegis.utils.prompt_templates import Message

logger = setup_logger(__name__)


def get_current_model_name() -> str:
    """
    Returns the name of the current LLM model to use.
    Falls back to 'llama3' if not set via environment variable.
    """
    try:
        response = requests.get("http://ollama:11434/api/tags")
        response.raise_for_status()
        models = response.json().get("models", [])
        if models:
            return models[0]["name"]
    except Exception as e:  # nosec: generalized fallback as e:
        logger.error(f"[LLM Backend] [ERROR] Could not retrieve model list from Ollama! Exception follows:\n\n{e}")
        pass


def format_prompt(messages: list[Message]) -> str:
    """
    Formats a list of Message objects into a single prompt string.
    Each message is prepended by its role.

    :param messages: List of Message(role, content) objects
    :return: A single prompt string for LLM input
    """

    prompt = ""
    for message in messages:
        prompt += f"<|{message.role}|> {message.content}"
        prompt += "<|assistant|>"
        return prompt
