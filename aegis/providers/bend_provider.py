# aegis/providers/bend_provider.py
"""
A concrete implementation of the BackendProvider for the BEND stack.
"""
import asyncio
import json
from typing import List, Dict, Any

import aiohttp

from aegis.exceptions import PlannerError, ToolExecutionError
from aegis.providers.base import BackendProvider
from aegis.schemas.backend import BendBackendConfig
from aegis.schemas.runtime import RuntimeExecutionConfig
from aegis.utils.logger import setup_logger
from aegis.utils.model_manifest_loader import get_formatter_hint
from aegis.utils.prompt_formatter import format_prompt

logger = setup_logger(__name__)


class BendProvider(BackendProvider):
    """
    Provider for interacting with a BEND (Backend Enhanced Neural Dispatch) stack.
    """

    def __init__(self, config: BendBackendConfig):
        self.config = config

    async def get_completion(self, messages: List[Dict[str, Any]], runtime_config: RuntimeExecutionConfig) -> str:
        """Gets a completion from the BEND KoboldCPP /generate endpoint."""
        formatter_hint = get_formatter_hint(runtime_config.llm_model_name)
        formatted_prompt = format_prompt(formatter_hint, messages)

        payload = {
            "prompt": formatted_prompt,
            "temperature": runtime_config.temperature,
            "max_context_length": runtime_config.max_context_length,
            "max_length": runtime_config.max_tokens_to_generate,
            "top_p": runtime_config.top_p,
            "top_k": runtime_config.top_k,
            "rep_pen": runtime_config.repetition_penalty,
        }

        logger.info(f"Sending prompt to BEND backend at {self.config.llm_url}")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.config.llm_url, json=payload, timeout=runtime_config.llm_planning_timeout) as response:
                    if not response.ok:
                        body = await response.text()
                        raise PlannerError(f"Failed to query BEND. Status: {response.status}, Body: {body}")
                    result = await response.json()
                    if "results" not in result or not result["results"] or "text" not in result["results"][0]:
                        raise PlannerError("Invalid response format from BEND: 'results' or 'text' key missing.")
                    return result["results"][0]["text"]
        except asyncio.TimeoutError as e:
            raise PlannerError("Query to BEND timed out.") from e
        except aiohttp.ClientError as e:
            raise PlannerError(f"Network error while querying BEND: {e}") from e

    async def get_speech(self, text: str) -> bytes:
        """Generates speech by calling the BEND voice proxy."""
        url = f"{self.config.voice_proxy_url}/speak"
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["X-API-Key"] = self.config.api_key
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json={"text": text}, headers=headers) as response:
                    response.raise_for_status()
                    return await response.read()
        except aiohttp.ClientError as e:
            raise ToolExecutionError(f"BEND speech synthesis failed: {e}") from e

    async def get_transcription(self, audio_bytes: bytes) -> str:
        """Transcribes audio by calling the BEND voice proxy."""
        url = f"{self.config.voice_proxy_url}/transcribe"
        headers = {}
        if self.config.api_key:
            headers["X-API-Key"] = self.config.api_key
        
        data = aiohttp.FormData()
        data.add_field('file', audio_bytes, filename='audio.wav', content_type='audio/wav')
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=data, headers=headers) as response:
                    response.raise_for_status()
                    result = await response.json()
                    return result.get("text", "[No text in transcription response]")
        except aiohttp.ClientError as e:
            raise ToolExecutionError(f"BEND audio transcription failed: {e}") from e