# aegis/providers/koboldcpp_provider.py
"""
A concrete implementation of the BackendProvider for a generic KoboldCPP backend.
"""
import asyncio
import json
from typing import List, Dict, Any

import aiohttp

from aegis.exceptions import PlannerError
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
        # Determine the correct prompt format using AEGIS's own manifest
        model_name = runtime_config.llm_model_name or "default"
        formatter_hint = get_formatter_hint(model_name)
        formatted_prompt = format_prompt(formatter_hint, messages)

        # Prepare payload for KoboldCPP's /generate endpoint
        # Generation parameters are read from the runtime config to allow overrides.
        payload = {
            "prompt": formatted_prompt,
            "temperature": runtime_config.temperature,
            "max_context_length": runtime_config.max_context_length,
            "max_length": runtime_config.max_tokens_to_generate,
            "top_p": runtime_config.top_p,
            "top_k": runtime_config.top_k,
            "rep_pen": runtime_config.repetition_penalty,
        }

        logger.info(f"Sending prompt to KoboldCPP backend at {self.config.llm_url}")
        logger.debug(f"KoboldCPP payload: {json.dumps(payload, indent=2)}")

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
