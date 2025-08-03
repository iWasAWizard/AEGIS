# aegis/providers/koboldcpp_provider.py
"""
A concrete implementation of the BackendProvider for the BEND stack using KoboldCPP.
"""
import asyncio
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Type

import httpx
from pydantic import BaseModel

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
    Provider for interacting with a BEND stack that uses KoboldCPP for its LLM.
    """

    def __init__(self, config: KoboldcppBackendConfig):
        self.config = config

    async def get_completion(
        self, messages: List[Dict[str, Any]], runtime_config: RuntimeExecutionConfig
    ) -> str:
        """Gets a completion from the BEND KoboldCPP /generate endpoint."""
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
            async with httpx.AsyncClient() as client:
                timeout = httpx.Timeout(runtime_config.llm_planning_timeout)
                response = await client.post(
                    self.config.llm_url, json=payload, timeout=timeout
                )
                if not response.is_success:
                    body = response.text
                    raise PlannerError(
                        f"Failed to query KoboldCPP. Status: {response.status_code}, Body: {body}"
                    )
                result = response.json()
                if (
                    "results" not in result
                    or not result["results"]
                    or "text" not in result["results"][0]
                ):
                    raise PlannerError(
                        "Invalid response format from KoboldCPP: 'results' or 'text' key missing."
                    )
                return result["results"][0]["text"]
        except httpx.TimeoutException as e:
            raise PlannerError("Query to KoboldCPP timed out.") from e
        except httpx.RequestError as e:
            raise PlannerError(f"Network error while querying KoboldCPP: {e}") from e

    async def get_structured_completion(
        self,
        messages: List[Dict[str, Any]],
        response_model: Type[BaseModel],
        runtime_config: RuntimeExecutionConfig,
    ) -> BaseModel:
        raise NotImplementedError(
            "KoboldCPP provider does not support structured completion."
        )

    async def get_speech(self, text: str) -> bytes:
        """Generates speech by calling the BEND voice proxy."""
        if not self.config.voice_proxy_url:
            raise ToolExecutionError("BEND voice proxy URL is not configured.")
        url = f"{self.config.voice_proxy_url}/speak"
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["X-API-Key"] = self.config.api_key

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url, json={"text": text}, headers=headers, timeout=60.0
                )
                response.raise_for_status()
                return response.read()
        except httpx.RequestError as e:
            raise ToolExecutionError(f"BEND speech synthesis failed: {e}") from e

    async def get_transcription(self, audio_bytes: bytes) -> str:
        """Transcribes audio by calling the BEND voice proxy."""
        if not self.config.voice_proxy_url:
            raise ToolExecutionError("BEND voice proxy URL is not configured.")
        url = f"{self.config.voice_proxy_url}/transcribe"
        headers = {}
        if self.config.api_key:
            headers["X-API-Key"] = self.config.api_key

        files = {"file": ("audio.wav", audio_bytes, "audio/wav")}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url, files=files, headers=headers, timeout=60.0
                )
                response.raise_for_status()
                result = response.json()
                return result.get("text", "[No text in transcription response]")
        except httpx.RequestError as e:
            raise ToolExecutionError(f"BEND audio transcription failed: {e}") from e

    async def ingest_document(
        self, file_path: str, source_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Ingests a document into the BEND RAG system."""
        if not self.config.rag_url:
            raise ToolExecutionError("BEND RAG URL is not configured.")

        url = f"{self.config.rag_url}/ingest"
        headers = {}
        if self.config.api_key:
            headers["X-API-Key"] = self.config.api_key

        p = Path(file_path)
        if not p.is_file():
            raise ToolExecutionError(
                f"Document for ingestion not found at: {file_path}"
            )

        try:
            with open(file_path, "rb") as f:
                files = {
                    "file": (
                        source_name or p.name,
                        f.read(),
                        "application/octet-stream",
                    )
                }
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        url, files=files, headers=headers, timeout=120.0
                    )
                    response.raise_for_status()
                    return response.json()
        except httpx.RequestError as e:
            raise ToolExecutionError(f"BEND document ingestion failed: {e}") from e
        except IOError as e:
            raise ToolExecutionError(
                f"Could not open file for ingestion: {file_path}. Error: {e}"
            )

    async def retrieve_knowledge(
        self, query: str, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Retrieves knowledge from the BEND RAG system."""
        if not self.config.rag_url:
            raise ToolExecutionError("BEND RAG URL is not configured.")

        url = f"{self.config.rag_url}/retrieve"
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["X-API-Key"] = self.config.api_key

        payload = {"query": query, "top_k": top_k}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url, json=payload, headers=headers, timeout=30.0
                )
                response.raise_for_status()
                return response.json()
        except httpx.RequestError as e:
            raise ToolExecutionError(f"BEND knowledge retrieval failed: {e}") from e
