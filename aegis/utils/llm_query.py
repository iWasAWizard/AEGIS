# aegis/utils/llm_query.py
"""
LLM query interface for sending prompts to an Ollama instance via HTTP.

This module provides an asynchronous function to send a structured system/user prompt
to an Ollama-compatible model over its HTTP API. It supports environment configuration
for model selection and API endpoint.
"""
import json
import os

import aiohttp
from aiohttp.client_exceptions import ClientResponseError

from aegis.utils.logger import setup_logger
from aegis.utils.prompt_formatter import format_prompt

logger = setup_logger(__name__)

OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://ollama:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")

if not OLLAMA_MODEL:
    raise EnvironmentError(
        "OLLAMA_MODEL environment variable must be set to a valid model name (e.g., 'llama3')."
    )

OLLAMA_FORMAT = os.getenv("OLLAMA_FORMAT", "json")


async def llm_query(
    system_prompt: str, user_prompt: str, model: str = None, ollama_url: str = None
) -> str:
    """Queries the configured Ollama model with separate system and user prompts.

    :param system_prompt: Instructions or context for the assistant.
    :type system_prompt: str
    :param user_prompt: The user's message or the main body of the prompt.
    :type user_prompt: str
    :param model: Optional override for the model name.
    :type model: str or None
    :param ollama_url: Optional override for the Ollama endpoint URL.
    :type ollama_url: str or None
    :return: The model-generated response as a string.
    :rtype: str
    :raises RuntimeError: If the HTTP request fails or the response is malformed.
    """
    effective_model = model or OLLAMA_MODEL
    effective_url = ollama_url or OLLAMA_API_URL

    # Construct the message history in the standard format
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    # Use the new, centralized formatter
    prompt = format_prompt(effective_model, messages)

    payload = {
        "model": effective_model,
        "prompt": prompt,
        "format": OLLAMA_FORMAT,  # Ensure the model outputs JSON
        "stream": False,
        "options": {
            "temperature": 0.5,  # Lower temperature for more deterministic tool use
            "top_k": 40,
            "top_p": 0.9,
        },
    }

    logger.info(
        f"Sending prompt to Ollama at {effective_url} using model '{effective_model}'"
    )
    logger.debug(f"Payload sent to Ollama: {json.dumps(payload, indent=2)}")

    try:
        async with aiohttp.ClientSession() as session:
            # Increased timeout to 3 minutes for slower models
            async with session.post(
                effective_url, json=payload, timeout=180
            ) as response:
                response.raise_for_status()
                result = await response.json()
    except ClientResponseError as cre:
        body = await cre.text()
        logger.error(f"Client error from Ollama ({cre.status}): {body}")
        raise RuntimeError(
            f"Failed to query Ollama. Status: {cre.status}, Body: {body}"
        ) from cre
    except asyncio.TimeoutError:
        logger.error(
            f"LLM query timed out after 180 seconds for model {effective_model}."
        )
        raise RuntimeError(
            f"LLM query timed out. The model may be too slow or stuck."
        ) from None
    except Exception as e:
        logger.exception("Unhandled error while querying Ollama")
        raise RuntimeError("Unexpected error during LLM query") from e

    if "response" not in result:
        logger.error(f"Missing 'response' field in Ollama result: {result}")
        raise RuntimeError("Invalid Ollama response format")

    logger.debug(f"LLM raw response: {result['response']}")
    return result["response"]
