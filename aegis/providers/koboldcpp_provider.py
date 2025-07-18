# aegis/providers/koboldcpp_provider.py
"""
A concrete implementation of the BackendProvider for a generic KoboldCPP backend.
"""
import asyncio
import json
from typing import List, Dict, Any, Optional

import aiohttp

from aegis.exceptions import PlannerError, ToolExecutionError
from aegis.providers.base import BackendProvider
from aegis.schemas.backend import KoboldcppBackendConfig
from aegis.schemas.runtime import RuntimeExecutionConfig
from aegis.utils.logger import setup_logger
from aegis.utils.model_manifest_loader import get_formatter_hint
from aegis.utils.prompt_formatter import format_prompt

logger = setup_logger(__name__)


class KoboldcppProvider(BackendProvider):
    """
    Provider for interacting with a standalone KoboldCPP /generate endpoint.
    """

    def __init__(self, config: KoboldcppBackendConfig):
        self.config = config

    async def get_completion(
        self, messages: List[Dict[str, Any]], runtime_config: RuntimeExecutionConfig
    ) -> str:
        """
        Gets a completion from the KoboldCPP /generate endpoint.
        """
        formatter_hint = get_formatter_hint(runtime_config.llm_model_name)
        formatted_prompt = format_prompt(formatter_hint, messages)

        # Build payload carefully, respecting runtime overrides but falling back to defaults.
        payload = {
            "prompt": formatted_prompt,
            "max_context_length": runtime_config.max_context_length,
            "temperature": (
                runtime_config.temperature
                if runtime_config.temperature is not None
                else self.config.temperature
            ),
            "max_length": (
                runtime_config.max_tokens_to_generate
                if runtime_config.max_tokens_to_generate is not None
                else self.config.max_tokens_to_generate
            ),
            "top_p": (
                runtime_config.top_p
                if runtime_config.top_p is not None
                else self.config.top_p
            ),
            "top_k": (
                runtime_config.top_k
                if runtime_config.top_k is not None
                else self.config.top_k
            ),
            "rep_pen": (
                runtime_config.repetition_penalty
                if runtime_config.repetition_penalty is not None
                else self.config.repetition_penalty
            ),
        }

        logger.info(f"Sending prompt to KoboldCPP backend at {self.config.llm_url}")
        logger.debug(f"KoboldCPP payload: {json.dumps(payload, indent=2)}")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.config.llm_url,
                    json=payload,
                    timeout=runtime_config.llm_planning_timeout,
                ) as response:
                    if not response.ok:
                        body = await response.text()
                        logger.error(
                            f"Error from KoboldCPP ({response.status}): {body}"
                        )
                        raise PlannerError(
                            f"Failed to query KoboldCPP. Status: {response.status}, Body: {body}"
                        )

                    result = await response.json()
                    if (
                        "results" not in result
                        or not result["results"]
                        or "text" not in result["results"][0]
                    ):
                        raise PlannerError(
                            "Invalid response format from KoboldCPP: 'results' or 'text' key missing."
                        )

                    return result["results"][0]["text"]
        except asyncio.TimeoutError as e:
            raise PlannerError("Query to KoboldCPP timed out.") from e
        except aiohttp.ClientError as e:
            raise PlannerError(f"Network error while querying KoboldCPP: {e}") from e

    async def get_speech(self, text: str) -> bytes:
        raise NotImplementedError(
            "KoboldcppProvider does not support speech synthesis."
        )

    async def get_transcription(self, audio_bytes: bytes) -> str:
        raise NotImplementedError(
            "KoboldcppProvider does not support audio transcription."
        )

    async def ingest_document(
        self, file_path: str, source_name: Optional[str] = None
    ) -> Dict[str, Any]:
        raise NotImplementedError(
            "KoboldcppProvider does not support document ingestion."
        )

    async def retrieve_knowledge(
        self, query: str, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError(
            "KoboldcppProvider does not support knowledge retrieval."
        )
