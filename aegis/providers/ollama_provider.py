# aegis/providers/ollama_provider.py
"""
A concrete implementation of the BackendProvider for an Ollama backend.
"""
import asyncio
import json
from typing import List, Dict, Any, Optional, Type

import aiohttp
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

    async def get_completion(
        self, messages: List[Dict[str, Any]], runtime_config: RuntimeExecutionConfig
    ) -> str:
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

        logger.info(f"Sending prompt to Ollama backend at {url}")
        logger.debug(f"Ollama payload: {json.dumps(payload, indent=2)}")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    timeout=runtime_config.llm_planning_timeout,
                ) as response:
                    if not response.ok:
                        body = await response.text()
                        raise PlannerError(
                            f"Failed to query Ollama. Status: {response.status}, Body: {body}"
                        )
                    result = await response.json()
                    if "message" not in result or "content" not in result["message"]:
                        raise PlannerError(
                            "Invalid response format from Ollama: 'message.content' key missing."
                        )
                    return result["message"]["content"]
        except asyncio.TimeoutError as e:
            raise PlannerError("Query to Ollama timed out.") from e
        except aiohttp.ClientError as e:
            raise PlannerError(f"Network error while querying Ollama: {e}") from e

    async def get_structured_completion(
        self, system_prompt: str, user_prompt: str, response_model: Type[BaseModel]
    ) -> BaseModel:
        """
        Gets a structured completion from Ollama by requesting a JSON object
        and validating it against the provided Pydantic model.
        """
        url = f"{self.config.llm_url}/api/chat"
        # We add a specific instruction to the system prompt to ensure JSON output
        json_system_prompt = (
            f"{system_prompt}\n\n"
            "Your response MUST be a single, valid JSON object that conforms to the user's requested schema. "
            "Do not include any other text, markdown, or explanations before or after the JSON object."
        )

        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": json_system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "format": "json",  # Explicitly request JSON output from Ollama
            "stream": False,
        }

        logger.info(f"Sending structured prompt to Ollama backend at {url}")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=300) as response:
                    response.raise_for_status()
                    llm_response_text = await response.text()

                    # Parse the JSON and validate against the Pydantic model
                    json_data = json.loads(llm_response_text)
                    # Ollama nests the actual response string inside a 'message' object
                    content_str = json_data.get("message", {}).get("content", "")
                    if not content_str:
                        raise PlannerError("Ollama returned an empty message content.")

                    # The content itself is a JSON string, so we parse it again
                    final_json = json.loads(content_str)
                    return response_model.model_validate(final_json)

        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            raise PlannerError(
                f"Network error during Ollama structured completion: {e}"
            ) from e
        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(
                f"Failed to parse or validate Ollama's JSON response. Error: {e}"
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
