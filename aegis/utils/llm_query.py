# aegis/utils/llm_query.py
"""
LLM query interface for dispatching prompts to a configured backend provider.
"""
from typing import List, Dict, Any

from aegis.exceptions import ConfigurationError
from aegis.providers.base import BackendProvider
from aegis.providers.bend_provider import BendProvider
from aegis.providers.ollama_provider import OllamaProvider
from aegis.providers.openai_provider import OpenAIProvider
from aegis.schemas.runtime import RuntimeExecutionConfig
from aegis.utils.backend_loader import get_backend_config
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


def get_provider_for_profile(profile_name: str) -> BackendProvider:
    """
    Factory function to get the correct provider instance based on a profile name.
    """
    backend_config = get_backend_config(profile_name)

    if backend_config.type == "bend":
        return BendProvider(config=backend_config)
    elif backend_config.type == "openai":
        return OpenAIProvider(config=backend_config)
    elif backend_config.type == "ollama":
        return OllamaProvider(config=backend_config)
    else:
        raise ConfigurationError(
            f"Unsupported backend provider type: '{backend_config.type}'"
        )


async def llm_query(
    system_prompt: str,
    user_prompt: str,
    runtime_config: RuntimeExecutionConfig,
) -> str:
    """
    Queries the configured LLM backend via its provider with system and user prompts.
    """
    logger.info(
        f"Dispatching LLM query using backend profile: '{runtime_config.backend_profile}'"
    )

    try:
        if runtime_config.backend_profile is None:
            raise ConfigurationError(
                "No backend profile specified in runtime configuration."
            )
        provider = get_provider_for_profile(runtime_config.backend_profile)
    except ConfigurationError as e:
        logger.exception(
            f"Failed to initialize backend provider for profile '{runtime_config.backend_profile}'"
        )
        # Re-raise as it's a critical setup failure
        raise

    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    # The provider is now responsible for all API calls and error handling.
    return await provider.get_completion(messages, runtime_config)
