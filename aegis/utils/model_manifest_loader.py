# aegis/utils/model_manifest_loader.py
"""
Utility for loading and accessing LLM model definitions from AEGIS's models.yaml.
"""
import functools
from pathlib import Path
from typing import List, Optional, Dict, Any

import yaml
from pydantic import BaseModel, Field, ValidationError

from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


class ModelEntry(BaseModel):
    """Represents a single model definition from aegis/models.yaml."""

    key: str
    name: str
    formatter_hint: str
    notes: Optional[str] = None


class ModelManifest(BaseModel):
    """Represents the entire collection of models defined in models.yaml."""

    models: List[ModelEntry] = Field(default_factory=list)


@functools.cache
def _load_and_parse_manifest() -> ModelManifest:
    """
    Loads, parses, and validates the models.yaml file.
    The @functools.cache decorator ensures this runs only once.
    """
    logger.info("Cache miss. Loading models.yaml from disk...")
    manifest_path = Path("models.yaml")  # Correct path inside container
    if not manifest_path.is_file():
        logger.warning(
            "models.yaml not found at root. Prompt formatting may be incorrect."
        )
        return ModelManifest(models=[])

    try:
        with manifest_path.open("r", encoding="utf-8") as f:
            raw_data = yaml.safe_load(f)
        return ModelManifest(**raw_data)
    except (yaml.YAMLError, ValidationError) as e:
        logger.exception(f"Failed to load or validate AEGIS model manifest: {e}")
        # Return an empty manifest as a safe fallback
        return ModelManifest(models=[])


def get_parsed_model_manifest() -> ModelManifest:
    """
    Returns the cached, parsed model manifest.
    Triggers the loading process on the first call.
    """
    return _load_and_parse_manifest()


def clear_model_manifest_cache():
    """Clears the cache for the model manifest loader."""
    _load_and_parse_manifest.cache_clear()
    logger.info("Cleared models.yaml cache.")


def get_formatter_hint(model_name: str) -> str:
    """
    Retrieves a formatter hint by its 'key' from the cached manifest.
    """
    default_formatter = "chatml"
    manifest = get_parsed_model_manifest()

    if not model_name or not manifest.models:
        return default_formatter

    search_term_lower = model_name.lower()
    for entry in manifest.models:
        if entry.key.lower() == search_term_lower:
            return entry.formatter_hint

    logger.warning(
        f"No formatter hint found for model '{model_name}'. Falling back to '{default_formatter}'."
    )
    return default_formatter