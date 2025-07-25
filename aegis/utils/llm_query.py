# aegis/utils/llm_query.py
"""
LLM query interface for dispatching prompts to a configured backend provider.
"""
from typing import List, Dict, Any

from aegis.exceptions import ConfigurationError
from aegis.providers.base import BackendProvider
from aegis.providers.koboldcpp_provider import KoboldcppProvider
from aegis.providers.ollama_provider import OllamaProvider
from aegis.providers.openai_provider import OpenAIProvider
from aegis.providers.vllm_provider import VllmProvider
from aegis.schemas.runtime import RuntimeExecutionConfig
from aegis.utils.backend_loader import get_backend_config
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


def get_provider_for_profile(profile_name: str) -> BackendProvider:
    """
    Factory function to get the correct provider instance based on a profile name.
    """
    backend_config = get_backend_config(profile_name)

    if backend_config.type == "koboldcpp":
        return KoboldcppProvider(config=backend_config)
    elif backend_config.type == "openai":
        return OpenAIProvider(config=backend_config)
    elif backend_config.type == "vllm":
        return VllmProvider(config=backend_config)
    elif backend_config.type == "ollama":
        return OllamaProvider(config=backend_config)
    else:
        raise ConfigurationError(
            f"Unsupported backend provider type: '{backend_config.type}'"
        )
