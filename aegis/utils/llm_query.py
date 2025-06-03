"""
LLM query interface for sending prompts to an Ollama instance via HTTP.

This module provides an asynchronous function to send a structured system/user prompt
to an Ollama-compatible model over its HTTP API. It supports environment configuration
for model selection and API endpoint.

Environment Variables
---------------------
OLLAMA_MODEL : str
    The name of the model to use (default: "llama3").
OLLAMA_API_URL : str
    The base URL of the Ollama server (default: "http://ollama:11434/api/generate").
"""

import os
import json
import aiohttp
from aiohttp.client_exceptions import ClientResponseError

from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)

OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://ollama:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")

if not OLLAMA_MODEL:
    raise EnvironmentError(
        "OLLAMA_MODEL environment variable must be set to a valid model name."
    )

# Optional content format specification
OLLAMA_FORMAT = os.getenv("OLLAMA_FORMAT", "json")


async def llm_query(
    system_prompt: str, user_prompt: str, model: str = None, ollama_url: str = None
) -> str:
    """
    Query the configured Ollama model using the provided system and user prompts.

    The prompts are embedded in a ChatML-style format and sent to the Ollama `/api/generate` endpoint. A non-streaming
    JSON response is expected from the server. If the request fails or the response is malformed, an exception is raised.

    :param system_prompt: Instructions or context for the assistant, typically setting tone or constraints.
    :type system_prompt: str
    :param user_prompt: The user's message to the assistant.
    :type user_prompt: str
    :param model: Optional override for model name.
    :type model: str
    :param ollama_url: Optional override for Ollama endpoint URL.
    :type ollama_url: str
    :return: Model-generated response as a string.
    :rtype: str
    :raises RuntimeError: If the HTTP request fails or response is improperly formatted.
    """
    effective_model = model or OLLAMA_MODEL
    effective_url = ollama_url or OLLAMA_API_URL

    prompt = f"<|system|>\n{system_prompt}\n\n<|user|>\n{user_prompt}"

    payload = {
        "model": effective_model,
        "prompt": prompt,
        "format": OLLAMA_FORMAT,
        "stream": False,
    }

    logger.info(
        "Sending prompt to Ollama at %s using model '%s'",
        effective_url,
        effective_model,
    )
    logger.debug("Payload: %s", payload)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(effective_url, json=payload) as response:
                response.raise_for_status()
                result = await response.json()
    except ClientResponseError as cre:
        logger.error("Client error from Ollama: %s", cre)
        raise RuntimeError("Failed to query Ollama") from cre
    except Exception as e:
        logger.exception("Unhandled error while querying Ollama")
        raise RuntimeError("Unexpected error during LLM query") from e

    if "response" not in result:
        logger.error("Missing 'response' field in Ollama result: %s", result)
        raise RuntimeError("Invalid Ollama response format")

    return result["response"]


# ----------------------------------------------------------------------------------------
# Below this line: Future extension hooks for multi-format support and model routing
# These can be enabled as needed for dynamic prompt formatting across backends
# ----------------------------------------------------------------------------------------
# def format_prompt_for_model(model_name: str, system_prompt: str, user_prompt: str) -> str:
#     if 'llama3' in model_name.lower():
#         return f'<|begin|>\n<|system|>\n{system_prompt}\n<|user|>\n{user_prompt}\n<|end|>'
#     return f'<|system|>\n{system_prompt}\n\n<|user|>\n{user_prompt}'
