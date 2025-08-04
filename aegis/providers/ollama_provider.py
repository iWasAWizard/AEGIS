# aegis/providers/ollama_provider.py
"""
A concrete implementation of the BackendProvider for an Ollama backend.
"""
import asyncio
import json
from typing import List, Dict, Any, Optional, Type, Union

import httpx
from pydantic import BaseModel, ValidationError

from aegis.exceptions import PlannerError, ToolExecutionError
from aegis.providers.base import BackendProvider
from aegis.schemas.backend import OllamaBackendConfig
from aegis.schemas.runtime import RuntimeExecutionConfig
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


class OllamaProvider(BackendProvider):
    """
    Provider for interacting with an Ollama /api/chat endpoint.
    """

    def __init__(self, config: OllamaBackendConfig):
        self.config = config
        logger.debug(
            f"OllamaProvider initialized with config: {config.model_dump_json()}"
        )

    async def get_completion(
        self,
        messages: List[Dict[str, Any]],
        runtime_config: RuntimeExecutionConfig,
        raw_response: bool = False,
    ) -> Union[str, Any]:
        """
        Gets a completion from the Ollama chat endpoint.
        """
        url = f"{self.config.llm_url}/api/chat"
        payload = {
            "model": self.config.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": (
                    runtime_config.temperature
                    if runtime_config.temperature is not None
                    else self.config.temperature
                ),
                "num_predict": (
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
                "repeat_penalty": (
                    runtime_config.repetition_penalty
                    if runtime_config.repetition_penalty is not None
                    else self.config.repetition_penalty
                ),
            },
        }

        # Filter out any None values from the options dict before sending
        payload["options"] = {
            k: v for k, v in payload["options"].items() if v is not None
        }

        logger.info(f"Sending prompt to Ollama backend.")
        logger.debug(f"Ollama final URL: {url}")
        logger.debug(f"Ollama payload: {json.dumps(payload, indent=2)}")

        try:
            async with httpx.AsyncClient() as client:
                timeout = httpx.Timeout(runtime_config.llm_planning_timeout)
                response = await client.post(url, json=payload, timeout=timeout)

                if not response.is_success:
                    body = response.text
                    logger.error(
                        f"Error from Ollama ({response.status_code}) at URL '{url}': {body}"
                    )
                    raise PlannerError(
                        f"Failed to query Ollama. Status: {response.status_code}, Body: {body}"
                    )

                if raw_response:
                    return response

                result = response.json()
                if "message" not in result or "content" not in result["message"]:
                    raise PlannerError(
                        "Invalid response format from Ollama: 'message.content' key missing."
                    )
                return result["message"]["content"]
        except httpx.TimeoutException as e:
            raise PlannerError("Query to Ollama timed out.") from e
        except httpx.RequestError as e:
            raise PlannerError(f"Network error while querying Ollama: {e}") from e

    async def get_structured_completion(
        self,
        messages: List[Dict[str, Any]],
        response_model: Type[BaseModel],
        runtime_config: RuntimeExecutionConfig,
    ) -> BaseModel:
        """
        Gets a structured completion from Ollama by requesting a JSON object
        and validating it against the provided Pydantic model.
        """
        url = f"{self.config.llm_url}/api/chat"

        payload = {
            "model": self.config.model,
            "messages": messages,
            "format": "json",  # Explicitly request JSON output from Ollama
            "stream": False,
        }

        logger.info(f"Sending structured prompt to Ollama backend.")
        logger.debug(f"Ollama final URL for structured completion: {url}")
        logger.debug(f"Ollama structured payload: {json.dumps(payload, indent=2)}")

        try:
            async with httpx.AsyncClient() as client:
                timeout = httpx.Timeout(runtime_config.llm_planning_timeout)
                response = await client.post(url, json=payload, timeout=timeout)

                if not response.is_success:
                    body = response.text
                    logger.error(
                        f"Error from Ollama ({response.status_code}) at URL '{url}': {body}"
                    )
                    response.raise_for_status()

                llm_response_json = response.json()

                # Ollama nests the actual response string inside a 'message' object
                content_str = llm_response_json.get("message", {}).get("content", "")
                if not content_str:
                    raise PlannerError("Ollama returned an empty message content.")

                # The content itself is a JSON string, so we parse it again
                final_json = json.loads(content_str)
                return response_model.model_validate(final_json)

        except (httpx.RequestError, httpx.TimeoutException) as e:
            logger.error(
                f"Network error during Ollama structured completion at URL '{url}': {e}"
            )
            raise PlannerError(
                f"Network error during Ollama structured completion: {e}"
            ) from e
        except (json.JSONDecodeError, ValidationError) as e:
            content_str = locals().get("content_str", "[Content not captured]")
            logger.error(
                f"Failed to parse or validate Ollama's JSON response. Raw content: '{content_str}'. Error: {e}"
            )
            raise PlannerError(
                "Ollama returned a malformed or invalid JSON object for the structured plan."
            ) from e

    async def get_speech(self, text: str) -> bytes:
        raise NotImplementedError("Ollama provider does not support speech synthesis.")

    async def get_transcription(self, audio_bytes: bytes) -> str:
        raise NotImplementedError(
            "Ollama provider does not support audio transcription."
        )

    async def ingest_document(
        self, file_path: str, source_name: Optional[str] = None
    ) -> Dict[str, Any]:
        raise NotImplementedError(
            "Ollama provider does not support document ingestion."
        )

    async def retrieve_knowledge(
        self, query: str, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError(
            "Ollama provider does not support knowledge retrieval."
        )
