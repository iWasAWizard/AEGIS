# aegis/utils/llm_query.py
"""
LLM query interface for sending prompts to a KoboldCPP instance via HTTP.

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
from aegis.utils.model_manifest_loader import (
    get_model_details_from_manifest,
)
from aegis.utils.prompt_formatter import format_prompt

logger = setup_logger(__name__)

KOBOLDCPP_DEFAULT_MODEL_HINT_ENV = os.getenv("KOBOLDCPP_MODEL")


async def _query_koboldcpp_api(
    session: aiohttp.ClientSession,
    url: str,
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
    Queries the configured KoboldCPP backend with system and user prompts.
    Uses `models.yaml` via `model_manifest_loader` to determine prompt formatting hints
    and potentially model-specific default context length.
    """
    formatter_hint, model_default_ctx, _ = get_model_details_from_manifest(
        model_key_from_config=runtime_config.llm_model_name,
        backend_default_identifier_env=KOBOLDCPP_DEFAULT_MODEL_HINT_ENV,
    )

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

    api_url = query_time_runtime_config.koboldcpp_api_url
    if not api_url:
        raise ConfigurationError("KoboldCPP backend: koboldcpp_api_url not configured.")

    logger.info(
        f"Sending prompt to KoboldCPP at {api_url} "
        f"(model hint: '{runtime_config.llm_model_name or KOBOLDCPP_DEFAULT_MODEL_HINT_ENV}', "
        f"formatter: '{formatter_hint}', context: {query_time_runtime_config.max_context_length})"
    )

    try:
        async with aiohttp.ClientSession() as session:
            response_text = await _query_koboldcpp_api(
                session,
                api_url,
                formatted_prompt,
                query_time_runtime_config,
            )
    except asyncio.TimeoutError as e:
        log_model_display_on_error = (
            runtime_config.llm_model_name or KOBOLDCPP_DEFAULT_MODEL_HINT_ENV
        )
        logger.error(
            f"LLM query to KoboldCPP timed out after {query_time_runtime_config.llm_planning_timeout}s "
            f"(model hint: '{log_model_display_on_error}', formatter: {formatter_hint})."
        )
        raise PlannerError(
            f"LLM query timed out. The model may be too slow or stuck."
        ) from e
    except aiohttp.ClientError as e:
        logger.exception(f"AIOHttp client error while querying KoboldCPP")
        raise PlannerError(f"Network error during LLM query: {e}") from e
    except ConfigurationError:
        raise
    except PlannerError:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error during LLM query to KoboldCPP: {e}")
        raise PlannerError(f"Unexpected error during LLM query: {e}") from e

    logger.debug(f"LLM raw response: {response_text}")
    return response_text
