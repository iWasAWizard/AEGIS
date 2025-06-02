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
    The base URL of the Ollama server (default: "http://ollama:11434/api/chat").
"""

import os

import aiohttp

from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)

OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://ollama:11434/api/chat")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")


async def llm_query(system_prompt: str, user_prompt: str) -> str:
    """
    Send a prompt to the LLM via Ollama's HTTP API.

    :param system_prompt: The system-level instruction for the model.
    :type system_prompt: str
    :param user_prompt: The user's input or query.
    :type user_prompt: str
    :return: The model's generated response text.
    :rtype: str
    """
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(OLLAMA_API_URL, json=payload) as response:
                response.raise_for_status()
                result = await response.json()
                return result.get("message", {}).get("content", "").strip()
    except Exception as e:
        logger.exception("Failed to query Ollama")
        return f"[LLM ERROR]: {e}"
