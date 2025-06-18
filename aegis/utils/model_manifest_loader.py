# aegis/utils/model_manifest_loader.py
"""
Utility for loading and accessing LLM model definitions from models.yaml.
"""
from pathlib import Path
from typing import List, Optional, Dict, Any

import yaml
from pydantic import BaseModel, Field

from aegis.exceptions import ConfigurationError
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)

_model_manifest_data: Optional[Dict[str, Any]] = None
_parsed_model_manifest: Optional["ModelManifest"] = None


class ModelEntry(BaseModel):
    """Represents a single model definition from models.yaml."""

    key: str = Field(
        ...,
        description="Unique key to identify the model configuration, used in llm_model_name.",
    )
    name: str = Field(
        ..., description="Human-readable name of the model or model family."
    )

    backend_model_name: Optional[str] = Field(
        None,
        description="The actual model name/tag the backend API expects (e.g., 'llama3:latest' for Ollama). If None, other logic determines the API model name.",
    )
    filename_pattern: Optional[List[str]] = Field(
        default_factory=list,
        description="List of case-insensitive patterns to match against backend default identifiers (like OLLAMA_MODEL or KOBOLDCPP_MODEL from .env) for inferring entry if 'key' isn't matched directly.",
    )
    formatter_hint: str = Field(
        ...,
        description="Hint for prompt_formatter.py (e.g., 'llama3', 'chatml', 'mistral').",
    )
    default_max_context_length: Optional[int] = Field(
        None, description="Default maximum context length for this model family."
    )
    quant_example: Optional[str] = Field(
        None, description="Example quantization, e.g., 'Q5_K_M'."
    )
    use_case: Optional[str] = Field(
        None, description="Primary intended use case for this model."
    )
    url: Optional[str] = Field(
        None,
        description="Direct download URL for the model file (e.g., GGUF from Hugging Face). Used by downloader tools.",
    )
    notes: Optional[str] = Field(
        None, description="Additional notes about the model or its setup."
    )

    class Config:
        extra = "ignore"


class ModelManifest(BaseModel):
    """Represents the entire collection of models defined in models.yaml."""

    models: List[ModelEntry] = Field(default_factory=list)


def load_model_manifest_data() -> Dict[str, Any]:
    """
    Loads the models.yaml file and caches the raw data.
    Returns raw dict to avoid Pydantic validation if file is temporarily malformed during edits.
    """
    global _model_manifest_data
    if _model_manifest_data is None:
        manifest_path = Path("models.yaml")
        if not manifest_path.is_file():
            logger.warning(
                "models.yaml not found in the project root. Model features relying on it may be limited."
            )
            _model_manifest_data = {"models": []}
            return _model_manifest_data
        try:
            with manifest_path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if data is None or not isinstance(data.get("models"), list):
                    logger.warning(
                        f"models.yaml is empty or 'models' key is not a list. Treating as empty."
                    )
                    _model_manifest_data = {"models": []}
                else:
                    _model_manifest_data = data
            logger.info(f"Raw model manifest data loaded from models.yaml.")
        except yaml.YAMLError as e:
            logger.exception("Failed to parse models.yaml")
            _model_manifest_data = {"models": []}
    return _model_manifest_data


def get_parsed_model_manifest() -> ModelManifest:
    """
    Parses the cached raw model manifest data using Pydantic.
    """
    global _parsed_model_manifest
    raw_data = load_model_manifest_data()

    if _parsed_model_manifest is None:
        try:
            _parsed_model_manifest = ModelManifest(**raw_data)
            logger.info(
                f"Successfully parsed models.yaml into ModelManifest with {len(_parsed_model_manifest.models)} entries."
            )
        except Exception as e:
            logger.exception(f"Failed to validate model manifest data: {e}")
            _parsed_model_manifest = ModelManifest(models=[])
            # Consider re-raise for stricter loading:
            # raise ConfigurationError(f"Failed to validate model manifest data: {e}") from e
    return _parsed_model_manifest


def get_model_entry(key_or_name_part: str) -> Optional[ModelEntry]:
    """
    Retrieves a model entry by its 'key' (case-insensitive) or by case-insensitive match
    of `key_or_name_part` against any string in an entry's `filename_pattern` list.
    Key match takes precedence.

    :param key_or_name_part: The key of the model or a part of its filename/tag.
    :type key_or_name_part: str
    :return: The ModelEntry if found, else None.
    :rtype: Optional[ModelEntry]
    """
    manifest = get_parsed_model_manifest()
    if not key_or_name_part or not manifest.models:
        return None

    search_term_lower = key_or_name_part.lower()

    for entry in manifest.models:
        if entry.key.lower() == search_term_lower:
            logger.debug(
                f"Found model entry by key: '{entry.key}' for search term '{key_or_name_part}'"
            )
            return entry

    for entry in manifest.models:
        if entry.filename_pattern:
            for pattern in entry.filename_pattern:
                if pattern.lower() in search_term_lower:
                    logger.debug(
                        f"Found model entry by filename pattern: '{entry.key}' (pattern: '{pattern}') for search term '{key_or_name_part}'"
                    )
                    return entry

    logger.debug(f"No model entry found for search term: '{key_or_name_part}'")
    return None


def get_model_details_from_manifest(
    model_key_from_config: Optional[str], backend_default_identifier_env: Optional[str]
) -> tuple[str, Optional[int], Optional[str]]:
    """
    Retrieves formatter_hint, default_max_context_length, and the effective backend_model_name.
    Search order:
    1. Uses `model_key_from_config` to find a ModelEntry by its `key`.
    2. If not found, uses `backend_default_identifier_env` to find a ModelEntry by `filename_pattern`.
    The `backend_model_name` returned is from the found ModelEntry if set, otherwise it's derived.
    Returns fallbacks (formatter 'chatml', no context_len, derived backend_name) if no specific match.

    :param model_key_from_config: The model key from AEGIS runtime config (e.g., RuntimeConfig.llm_model_name).
    :type model_key_from_config: Optional[str]
    :param backend_default_identifier_env: The model name/tag/filename from environment variables
                                           (e.g., OLLAMA_MODEL, KOBOLDCPP_MODEL).
    :type backend_default_identifier_env: Optional[str]
    :return: Tuple of (formatter_hint, default_max_context_length, effective_backend_model_name).
    :rtype: tuple[str, Optional[int], Optional[str]]
    """
    default_formatter = "chatml"
    default_ctx_len = None

    model_entry: Optional[ModelEntry] = None
    found_by: Optional[str] = None

    if model_key_from_config:
        model_entry = get_model_entry(model_key_from_config)
        if model_entry:
            found_by = f"key '{model_key_from_config}'"

    if not model_entry and backend_default_identifier_env:
        # get_model_entry will try key match first if backend_default_identifier_env happens to be a key
        # then it will try filename_pattern.
        model_entry = get_model_entry(backend_default_identifier_env)
        if model_entry:
            found_by = f"env_var_match '{backend_default_identifier_env}' (matched entry {model_entry.key})"

    if model_entry:
        logger.debug(
            f"Using model details from entry '{model_entry.key}' (found by {found_by}) from models.yaml."
        )
        # Use backend_model_name from entry if available, otherwise use the key that found it, or the env var.
        effective_backend_model_name = (
            model_entry.backend_model_name
            or (
                model_key_from_config
                if found_by and model_key_from_config in found_by
                else None
            )
            or (
                backend_default_identifier_env
                if found_by and backend_default_identifier_env in found_by
                else None
            )
            or model_entry.key
        )  # Fallback to entry key if others don't make sense

        return (
            model_entry.formatter_hint,
            model_entry.default_max_context_length,
            effective_backend_model_name,
        )

    # Fallback if no entry found
    log_search_terms = f"config_key: '{model_key_from_config}', env_default: '{backend_default_identifier_env}'"
    logger.warning(
        f"No specific model entry found in models.yaml using {log_search_terms}. "
        f"Falling back to formatter: '{default_formatter}'. "
        f"Backend model name for API will be derived from config or env var directly."
    )
    # If no models.yaml entry, the backend model name will be what was passed in or the env default.
    # This is important: if llm_model_name was "my-key" but "my-key" isn't in models.yaml,
    # we still might want to pass "my-key" to the backend if it's a valid backend model name.
    final_backend_name_for_api = model_key_from_config or backend_default_identifier_env
    return default_formatter, default_ctx_len, final_backend_name_for_api
