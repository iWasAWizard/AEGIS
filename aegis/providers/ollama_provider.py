# aegis/providers/ollama_provider.py
"""
A concrete implementation of the BackendProvider for a generic Ollama backend.
"""
import asyncio
import json
from typing import List, Dict, Any, Optional

import aiohttp

from aegis.exceptions import PlannerError, ToolExecutionError
from aegis.providers.base import BackendProvider
from aegis.schemas.backend import OllamaBackendConfig
from aegis.schemas.runtime import RuntimeExecutionConfig
from aegis.utils.logger import setup_logger
from aegis.utils.model_manifest_loader import get_formatter_hint
from aegis.utils.prompt_formatter import format_prompt

logger = setup_logger(__name__)


class OllamaProvider(BackendProvider):
    """
    Provider for interacting with a standalone Ollama /api/chat endpoint.
    """

    def __init__(self, config: OllamaBackendConfig):
        self.config = config

    async def get_completion(
        self, messages: List[Dict[str, Any]], runtime_config: RuntimeExecutionConfig
    ) -> str:
        """
        Gets a completion from the Ollama /api/chat endpoint.
        """
        # The URL is updated to the correct endpoint
        chat_url = self.config.llm_url.replace("/generate", "/chat")

        # Build payload carefully, respecting runtime overrides but falling back to defaults.
        options = {
            "temperature": (
                runtime_config.temperature
                if runtime_config.temperature is not None
                else self.config.temperature
            ),
            "num_ctx": runtime_config.max_context_length,
            "top_k": (
                runtime_config.top_k
                if runtime_config.top_k is not None
                else self.config.top_k
            ),
            "top_p": (
                runtime_config.top_p
                if runtime_config.top_p is not None
                else self.config.top_p
            ),
            "repeat_penalty": (
                runtime_config.repetition_penalty
                if runtime_config.repetition_penalty is not None
                else self.config.repetition_penalty
            ),
            # The number of tokens to generate is also an option for the chat endpoint
            "num_predict": (
                runtime_config.max_tokens_to_generate
                if runtime_config.max_tokens_to_generate is not None
                else self.config.max_tokens_to_generate
            ),
        }

        payload = {
            "model": runtime_config.llm_model_name,
            # We now pass the structured messages directly
            "messages": messages,
            "stream": False,
            "options": {k: v for k, v in options.items() if v is not None},
        }

        logger.info(f"Sending prompt to Ollama chat backend at {chat_url}")
        logger.debug(f"Ollama payload: {json.dumps(payload, indent=2)}")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    chat_url,
                    json=payload,
                    timeout=(
                        aiohttp.ClientTimeout(total=runtime_config.llm_planning_timeout)
                        if runtime_config.llm_planning_timeout is not None
                        else None
                    ),
                ) as response:
                    if not response.ok:
                        body = await response.text()
                        logger.error(f"Error from Ollama ({response.status}): {body}")
                        raise PlannerError(
                            f"Failed to query Ollama. Status: {response.status}, Body: {body}"
                        )

                    result = await response.json()
                    # The response structure is different for /api/chat
                    if "message" not in result or "content" not in result["message"]:
                        raise PlannerError(
                            "Invalid response format from Ollama chat: 'message' or 'content' key missing."
                        )

                    return result["message"]["content"]
        except asyncio.TimeoutError as e:
            raise PlannerError("Query to Ollama timed out.") from e
        except aiohttp.ClientError as e:
            raise PlannerError(f"Network error while querying Ollama: {e}") from e

    async def get_speech(self, text: str) -> bytes:
        raise NotImplementedError("Ollama provider does not support speech synthesis.")

    async def get_transcription(self, audio_bytes: bytes) -> str:
        raise NotImplementedError(
            "Ollama provider does not support audio transcription."
        )

    async def ingest_document(
        self, file_path: str, source_name: Optional[str] = None
    ) -> Dict[str, Any]:
        raise NotImplementedError("OllamaProvider does not support document ingestion.")

    async def retrieve_knowledge(
        self, query: str, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError(
            "OllamaProvider does not support knowledge retrieval."
        )
