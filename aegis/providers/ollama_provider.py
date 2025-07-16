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
    Provider for interacting with a standalone Ollama /api/generate endpoint.
    """

    def __init__(self, config: OllamaBackendConfig):
        self.config = config

    async def get_completion(
        self, messages: List[Dict[str, Any]], runtime_config: RuntimeExecutionConfig
    ) -> str:
        """
        Gets a completion from the Ollama /generate endpoint.
        """
        if runtime_config.llm_model_name is None:
            raise PlannerError("llm_model_name must be specified in runtime_config.")
        formatter_hint = get_formatter_hint(runtime_config.llm_model_name)
        formatted_prompt = format_prompt(formatter_hint, messages)

        payload = {
            "model": runtime_config.llm_model_name,  # Ollama requires the model name in the payload
            "prompt": formatted_prompt,
            "stream": False,
            "options": {
                "temperature": runtime_config.temperature,
                "num_ctx": runtime_config.max_context_length,
                "top_k": runtime_config.top_k,
                "top_p": runtime_config.top_p,
                "repeat_penalty": runtime_config.repetition_penalty,
            },
        }

        logger.info(f"Sending prompt to Ollama backend at {self.config.llm_url}")
        logger.debug(f"Ollama payload: {json.dumps(payload, indent=2)}")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.config.llm_url,
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
                    if "response" not in result:
                        raise PlannerError(
                            "Invalid response format from Ollama: 'response' key missing."
                        )

                    return result["response"]
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
