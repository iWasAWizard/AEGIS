# aegis/providers/vllm_provider.py
"""
A concrete implementation of the BackendProvider for a vLLM backend.
"""
import asyncio
import json
import os
from typing import List, Dict, Any, Optional, Type

import httpx
from pydantic import BaseModel

from aegis.exceptions import PlannerError, ToolExecutionError
from aegis.providers.base import BackendProvider
from aegis.schemas.backend import VllmBackendConfig
from aegis.schemas.runtime import RuntimeExecutionConfig
from aegis.utils.logger import setup_logger
from aegis.utils.tracing import log_generation

try:
    import instructor
    from openai import OpenAI
except ImportError:
    instructor = None
    OpenAI = None

logger = setup_logger(__name__)


class VllmProvider(BackendProvider):
    """
    Provider for interacting with a vLLM OpenAI-compatible /v1/chat/completions endpoint.
    """

    def __init__(self, config: VllmBackendConfig):
        self.config = config

    async def get_completion(
        self, messages: List[Dict[str, Any]], runtime_config: RuntimeExecutionConfig
    ) -> str:
        """
        Gets a completion from the vLLM chat endpoint.
        """
        # Build payload carefully, respecting runtime overrides but falling back to defaults.
        payload = {
            "model": self.config.model,
            "messages": messages,
            "stream": False,
            "temperature": (
                runtime_config.temperature
                if runtime_config.temperature is not None
                else self.config.temperature
            ),
            "max_tokens": (
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
            "repetition_penalty": (
                runtime_config.repetition_penalty
                if runtime_config.repetition_penalty is not None
                else self.config.repetition_penalty
            ),
        }
        # Filter out any None values from the payload before sending
        payload = {k: v for k, v in payload.items() if v is not None}

        logger.info(f"Sending prompt to vLLM chat backend at {self.config.llm_url}")
        logger.debug(f"vLLM payload: {json.dumps(payload, indent=2)}")

        try:
            async with httpx.AsyncClient() as client:
                timeout = httpx.Timeout(runtime_config.llm_planning_timeout)
                response = await client.post(
                    self.config.llm_url, json=payload, timeout=timeout
                )
                try:
                    _model = getattr(self.config, "model", None) or getattr(
                        response, "model", None
                    )
                    _prompt = locals().get("messages", None)
                    _output = getattr(response, "choices", None) or str(response)
                    _usage = {}
                    _u = getattr(response, "usage", None)
                    for k in ("prompt_tokens", "completion_tokens", "total_tokens"):
                        if hasattr(_u, k):
                            _usage[k] = getattr(_u, k)
                    if os.getenv("AEGIS_TRACE_GENERATIONS", "1") != "0":
                        log_generation(
                            run_id=None,
                            model=_model,
                            prompt=_prompt,
                            output=_output,
                            usage=_usage,
                            meta={"provider": "vllm"},
                        )
                except Exception:
                    pass

                if not response.is_success:
                    body = response.text
                    logger.error(f"Error from vLLM ({response.status_code}): {body}")
                    raise PlannerError(
                        f"Failed to query vLLM. Status: {response.status_code}, Body: {body}"
                    )

                result = response.json()
                if (
                    "choices" not in result
                    or not result["choices"]
                    or "message" not in result["choices"][0]
                    or "content" not in result["choices"][0]["message"]
                ):
                    raise PlannerError(
                        "Invalid response format from vLLM chat: expected 'choices[0].message.content' key missing."
                    )

                return result["choices"][0]["message"]["content"]
        except httpx.TimeoutException as e:
            raise PlannerError("Query to vLLM timed out.") from e
        except httpx.RequestError as e:
            raise PlannerError(f"Network error while querying vLLM: {e}") from e

    async def get_structured_completion(
        self,
        messages: List[Dict[str, Any]],
        response_model: Type[BaseModel],
        runtime_config: RuntimeExecutionConfig,
    ) -> BaseModel:
        if not instructor or not OpenAI:
            raise ToolExecutionError(
                "The 'instructor' and 'openai' libraries are required for structured completion."
            )
        base_url = self.config.llm_url.rsplit("/", 1)[0]
        client = instructor.patch(OpenAI(base_url=base_url, api_key="not-needed"))

        response = await client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            response_model=response_model,
        )
        return response

    async def get_speech(self, text: str) -> bytes:
        raise NotImplementedError("vLLM provider does not support speech synthesis.")

    async def get_transcription(self, audio_bytes: bytes) -> str:
        raise NotImplementedError("vLLM provider does not support audio transcription.")

    async def ingest_document(
        self, file_path: str, source_name: Optional[str] = None
    ) -> Dict[str, Any]:
        raise NotImplementedError("vLLM provider does not support document ingestion.")

    async def retrieve_knowledge(
        self, query: str, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError("vLLM provider does not support knowledge retrieval.")
