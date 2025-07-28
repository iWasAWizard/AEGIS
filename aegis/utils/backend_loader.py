# aegis/utils/backend_loader.py
"""
Utility for loading and resolving backend configurations from the manifest.
"""
from pathlib import Path
from typing import Union, Any

import yaml
from pydantic import ValidationError

from aegis.exceptions import ConfigurationError
from aegis.schemas.backend import (
    OllamaBackendConfig,
    OpenAIBackendConfig,
    VllmBackendConfig,
    BaseBackendConfig,
)
from aegis.schemas.settings import settings
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)

_backend_manifest_cache = None


def _load_manifest_from_file() -> dict:
    """Loads the backends.yaml file and caches it in memory."""
    global _backend_manifest_cache
    if _backend_manifest_cache is None:
        logger.info("Cache miss. Loading backends.yaml from disk...")
        manifest_path = Path("backends.yaml")
        if not manifest_path.is_file():
            raise ConfigurationError("backends.yaml not found in the root directory.")
        try:
            with manifest_path.open("r", encoding="utf-8") as f:
                _backend_manifest_cache = yaml.safe_load(f)
        except yaml.YAMLError as e:
            logger.exception("Failed to parse backends.yaml")
            raise ConfigurationError(f"Invalid YAML in backends.yaml: {e}") from e
    return _backend_manifest_cache


def get_backend_config(profile_name: str) -> Any:
    """
    Loads a specific backend's configuration and resolves secrets.
    """
    manifest_data = _load_manifest_from_file()

    backend_list = manifest_data.get("backends", [])
    backend_config_raw = next(
        (b for b in backend_list if b.get("profile_name") == profile_name), None
    )

    if not backend_config_raw:
        raise ConfigurationError(
            f"Backend profile '{profile_name}' not found in backends.yaml."
        )

    # Resolve secret placeholders like ${BEND_API_KEY}
    for key, value in backend_config_raw.items():
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            secret_key = value[2:-1]
            secret_value = getattr(settings, secret_key.upper(), None)
            if secret_value is None:
                logger.warning(
                    f"Secret '{secret_key}' for backend '{profile_name}' not found in environment or .env file. "
                    "This might be okay if it's optional."
                )
            backend_config_raw[key] = secret_value

    try:
        # Determine which Pydantic model to use based on the 'type' field
        backend_type = backend_config_raw.get("type")
        if backend_type == "ollama":
            return OllamaBackendConfig(**backend_config_raw)
        elif backend_type == "openai":
            return OpenAIBackendConfig(**backend_config_raw)
        elif backend_type == "vllm":
            return VllmBackendConfig(**backend_config_raw)
        else:
            raise ConfigurationError(
                f"Unknown backend type '{backend_type}' in profile '{profile_name}'."
            )
    except ValidationError as e:
        logger.error(f"Validation error for backend profile '{profile_name}': {e}")
        raise ConfigurationError(
            f"Invalid configuration for backend profile '{profile_name}': {e}"
        ) from e


def clear_backend_manifest_cache():
    """Clears the in-memory cache for backends.yaml."""
    global _backend_manifest_cache
    _backend_manifest_cache = None
    logger.info("Cleared backends.yaml cache.")
