# aegis/utils/llm_query.py
"""
LLM query interface for sending prompts to an Ollama or KoboldCPP instance via HTTP.

This module provides an asynchronous function to send a structured system/user prompt
to a configured LLM backend. It supports environment configuration
for model selection and API endpoint.
"""
import asyncio
import json
import os
from typing import Optional

import aiohttp

from aegis.exceptions import PlannerError, ConfigurationError
from aegis.schemas.runtime import RuntimeExecutionConfig
from aegis.utils.logger import setup_logger
from aegis.utils.prompt_formatter import format_prompt
from aegis.utils.model_manifest_loader import (
    get_model_details_from_manifest,
)

logger = setup_logger(__name__)

OLLAMA_DEFAULT_MODEL_ENV = os.getenv("OLLAMA_MODEL")
KOBOLDCPP_DEFAULT_MODEL_HINT_ENV = os.getenv("KOBOLDCPP_MODEL")

OLLAMA_FORMAT = os.getenv("OLLAMA_FORMAT", "json")


async def _query_ollama_api(
    session: aiohttp.ClientSession,
    url: str,
    model_name: str,
    formatted_prompt: str,
    runtime_config: RuntimeExecutionConfig,
) -> str:
    """Sends a request to the Ollama /api/generate endpoint."""
    payload = {
        "model": model_name,
        "prompt": formatted_prompt,
        "format": OLLAMA_FORMAT,
        "stream": False,
        "options": {
            "temperature": runtime_config.temperature,
            "num_ctx": runtime_config.max_context_length,
            "top_k": runtime_config.top_k,
            "top_p": runtime_config.top_p,
            "repeat_penalty": runtime_config.repetition_penalty,
        },
    }
    if runtime_config.max_tokens_to_generate > 0:
        payload["options"]["num_predict"] = runtime_config.max_tokens_to_generate

    logger.debug(f"Ollama payload: {json.dumps(payload, indent=2)}")
    async with session.post(
        url, json=payload, timeout=runtime_config.llm_planning_timeout
    ) as response:
        if not response.ok:
            body = await response.text()
            logger.error(f"Error from Ollama ({response.status}): {body}")
            raise PlannerError(
                f"Failed to query Ollama. Status: {response.status}, Body: {body}"
            )
        result = await response.json()
        if "response" not in result:
            logger.error(f"Missing 'response' field in Ollama result: {result}")
            raise PlannerError(
                "Invalid Ollama response format: 'response' key is missing."
            )
        return result["response"]


async def _query_koboldcpp_api(
    session: aiohttp.ClientSession,
    url: str,
    model_name_hint: Optional[str],
    formatted_prompt: str,
    runtime_config: RuntimeExecutionConfig,
) -> str:
    """Sends a request to the KoboldCPP /api/v1/generate endpoint."""
    payload = {
        "prompt": formatted_prompt,
        "temperature": runtime_config.temperature,
        "max_context_length": runtime_config.max_context_length,
        "max_length": runtime_config.max_tokens_to_generate,
        "top_p": runtime_config.top_p,
        "top_k": runtime_config.top_k,
        "rep_pen": runtime_config.repetition_penalty,
    }
    logger.debug(f"KoboldCPP payload: {json.dumps(payload, indent=2)}")
    async with session.post(
        url, json=payload, timeout=runtime_config.llm_planning_timeout
    ) as response:
        if not response.ok:
            body = await response.text()
            logger.error(
                f"Error from LLM Backend (KoboldCPP) ({response.status}): {body}"
            )
            raise PlannerError(
                f"Failed to query LLM Backend. Status: {response.status}, Body: {body}"
            )
        result = await response.json()
        if (
            "results" not in result
            or not isinstance(result["results"], list)
            or not result["results"]
        ):
            logger.error(
                f"Invalid LLM Backend response format. 'results' missing or empty: {result}"
            )
            raise PlannerError(
                "Invalid LLM Backend response format: 'results' key is malformed."
            )
        if "text" not in result["results"][0]:
            logger.error(
                f"Invalid LLM Backend response format. 'text' missing in results[0]: {result}"
            )
            raise PlannerError(
                "Invalid LLM Backend response format: 'text' key missing in results[0]."
            )
        return result["results"][0]["text"]


async def llm_query(
    system_prompt: str,
    user_prompt: str,
    runtime_config: RuntimeExecutionConfig,
) -> str:
    """
    Queries the configured LLM backend (Ollama or KoboldCPP) with system and user prompts.
    Uses `models.yaml` via `model_manifest_loader` to determine prompt formatting hints
    and potentially model-specific default context length.
    """
    backend_type = runtime_config.llm_backend_type

    env_default_for_backend: Optional[str] = None
    if backend_type == "ollama":
        env_default_for_backend = OLLAMA_DEFAULT_MODEL_ENV
    elif backend_type == "koboldcpp":
        env_default_for_backend = KOBOLDCPP_DEFAULT_MODEL_HINT_ENV

    formatter_hint, model_default_ctx, effective_backend_model_name_from_manifest = (
        get_model_details_from_manifest(
            model_key_from_config=runtime_config.llm_model_name,
            backend_default_identifier_env=env_default_for_backend,
        )
    )

    # If effective_backend_model_name_from_manifest is None, it means models.yaml lookup failed.
    # In this case, the name sent to the API will be runtime_config.llm_model_name (if set)
    # or the backend's environment variable default (e.g. OLLAMA_MODEL_ENV).
    # This `api_payload_model_name` is what gets sent to the backend API.
    api_payload_model_name = (
        effective_backend_model_name_from_manifest
        or runtime_config.llm_model_name
        or env_default_for_backend
    )

    if backend_type == "ollama" and not api_payload_model_name:
        raise ConfigurationError(
            "Ollama backend: Cannot determine model name for API payload. "
            "Ensure llm_model_name in config or OLLAMA_MODEL env var is set to a valid Ollama tag, "
            "and/or models.yaml has a matching entry with a 'backend_model_name'."
        )
    # For KoboldCPP, api_payload_model_name is not used in its _query_koboldcpp_api payload,
    # so it being None is acceptable if relying on pre-loaded model.

    query_time_runtime_config = runtime_config.model_copy(deep=True)
    pydantic_default_max_context = RuntimeExecutionConfig.model_fields[
        "max_context_length"
    ].default
    if (
        model_default_ctx is not None
        and query_time_runtime_config.max_context_length == pydantic_default_max_context
    ):
        logger.info(
            f"Overriding max_context_length from Pydantic default ({pydantic_default_max_context}) "
            f"to models.yaml default ({model_default_ctx}) for model associated with formatter hint '{formatter_hint}'."
        )
        query_time_runtime_config.max_context_length = model_default_ctx

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    formatted_prompt = format_prompt(formatter_hint, messages)

    api_url: Optional[str] = None
    query_func = None

    if backend_type == "ollama":
        api_url = query_time_runtime_config.ollama_api_url
        query_func = _query_ollama_api
        if not api_url:
            raise ConfigurationError("Ollama backend: ollama_api_url not configured.")
        if not api_payload_model_name:
            raise ConfigurationError(
                "Ollama backend: model name for API payload is missing."
            )
    elif backend_type == "koboldcpp":
        api_url = query_time_runtime_config.koboldcpp_api_url
        query_func = _query_koboldcpp_api
        if not api_url:
            raise ConfigurationError(
                "KoboldCPP backend: koboldcpp_api_url not configured."
            )
        # api_payload_model_name is passed as model_name_hint to _query_koboldcpp_api
    else:
        raise ConfigurationError(f"Unsupported llm_backend_type: {backend_type}")

    logger.info(
        f"Sending prompt to {backend_type.upper()} at {api_url} "
        f"(model for API: '{api_payload_model_name or '(KoboldCPP pre-loaded)'}', formatter: '{formatter_hint}', "
        f"context: {query_time_runtime_config.max_context_length})"
    )

    try:
        async with aiohttp.ClientSession() as session:
            # For _query_ollama_api, api_payload_model_name is the actual model tag for the payload.
            # For _query_koboldcpp_api, it's passed as model_name_hint, not used in payload.
            response_text = await query_func(  # type: ignore
                session,
                api_url,  # type: ignore
                api_payload_model_name,
                formatted_prompt,
                query_time_runtime_config,
            )
    except asyncio.TimeoutError as e:
        log_model_display_on_error = api_payload_model_name or "(KoboldCPP pre-loaded)"
        logger.error(
            f"LLM query to {backend_type.upper()} timed out after {query_time_runtime_config.llm_planning_timeout}s "
            f"(model: '{log_model_display_on_error}', formatter: {formatter_hint})."
        )
        raise PlannerError(
            f"LLM query timed out. The model may be too slow or stuck."
        ) from e
    except aiohttp.ClientError as e:
        logger.exception(f"AIOHttp client error while querying {backend_type.upper()}")
        raise PlannerError(f"Network error during LLM query: {e}") from e
    except ConfigurationError:
        raise
    except PlannerError:
        raise
    except Exception as e:
        logger.exception(
            f"Unexpected error during LLM query to {backend_type.upper()}: {e}"
        )
        raise PlannerError(f"Unexpected error during LLM query: {e}") from e

    logger.debug(f"LLM raw response: {response_text}")
    return response_text
