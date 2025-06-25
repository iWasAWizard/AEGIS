# aegis/utils/model_manifest_loader.py
"""
Utility for loading and accessing LLM model definitions from AEGIS's models.yaml.
"""
from pathlib import Path
from typing import List, Optional, Dict, Any

import yaml
from pydantic import BaseModel, Field

from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)

_model_manifest_data: Optional[Dict[str, Any]] = None
_parsed_model_manifest: Optional["ModelManifest"] = None


class ModelEntry(BaseModel):
    """Represents a single model definition from aegis/models.yaml."""
    key: str
    name: str
    formatter_hint: str
    notes: Optional[str] = None


class ModelManifest(BaseModel):
    """Represents the entire collection of models defined in models.yaml."""
    models: List[ModelEntry] = Field(default_factory=list)


def load_model_manifest_data() -> Dict[str, Any]:
    """Loads the aegis/models.yaml file and caches the raw data."""
    global _model_manifest_data
    if _model_manifest_data is None:
        # This now correctly points to AEGIS's own config file.
        manifest_path = Path("aegis/models.yaml")
        if not manifest_path.is_file():
            logger.warning(
                "aegis/models.yaml not found. Prompt formatting may be incorrect."
            )
            _model_manifest_data = {"models": []}
            return _model_manifest_data
        try:
            with manifest_path.open("r", encoding="utf-8") as f:
                _model_manifest_data = yaml.safe_load(f)
            logger.info("AEGIS model manifest for formatter hints loaded.")
        except yaml.YAMLError as e:
            logger.exception("Failed to parse aegis/models.yaml")
            _model_manifest_data = {"models": []}
    return _model_manifest_data


def get_parsed_model_manifest() -> ModelManifest:
    """Parses the cached raw model manifest data using Pydantic."""
    global _parsed_model_manifest
    raw_data = load_model_manifest_data()
    if _parsed_model_manifest is None:
        try:
            _parsed_model_manifest = ModelManifest(**raw_data)
        except Exception as e:
            logger.exception(f"Failed to validate AEGIS model manifest data: {e}")
            _parsed_model_manifest = ModelManifest(models=[])
    return _parsed_model_manifest


def get_formatter_hint(model_name: str) -> str:
    """Retrieves a formatter hint by its 'key'."""
    default_formatter = "chatml"
    manifest = get_parsed_model_manifest()
    if not model_name or not manifest.models:
        return default_formatter

    search_term_lower = model_name.lower()
    for entry in manifest.models:
        if entry.key.lower() == search_term_lower:
            return entry.formatter_hint

    logger.warning(f"No formatter hint found for model '{model_name}'. Falling back to '{default_formatter}'.")
    return default_formatter