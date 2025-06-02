"""Loads and validates agent configuration from file, profile, or dictionary.

Supports YAML, JSON, and profile resolution via the config loader."""

import json
from pathlib import Path

import yaml
from dotenv import load_dotenv

from aegis.schemas.config import AgentConfig
from aegis.utils.load_config_profile import load_config_profile
from aegis.utils.logger import setup_logger
from aegis.utils.type_resolver import resolve_dotted_type

load_dotenv()

logger = setup_logger(__name__)


def load_agent_config(
        config_file: Path = None, profile: str = None, raw_config: dict = None
) -> AgentConfig:
    """
    Load and validate an AgentConfig from one of several sources (JSON or YAML).
    """
    if config_file:
        try:
            logger.info(f"Loading config from file: {config_file}")
            ext = config_file.suffix.lower()
            if ext == ".json":
                config_data = json.loads(config_file.read_text())
            elif ext in [".yaml", ".yml"]:
                config_data = yaml.safe_load(config_file.read_text())
            else:
                raise ValueError(f"Unsupported config file format: {ext}")
        except Exception as e:
            logger.exception(f"[config_loader] Error: {e}")
            logger.error(f"Failed to parse config file: {e}")
            raise
    elif profile:
        try:
            logger.info(f"Loading config profile: {profile}")
            return load_config_profile(profile)
        except Exception as e:
            logger.exception(f"[config_loader] Error: {e}")
            logger.error(f"Failed to load config profile '{profile}': {e}")
            raise
    elif raw_config:
        logger.info("Using inline raw config dict")
        config_data = raw_config
    else:
        raise ValueError("Must provide either config_file, profile, or raw_config.")

    # Resolve dotted type if needed
    if "state_type" in config_data and isinstance(config_data["state_type"], str):
        logger.debug(
            f"Resolving dotted type for state_type: {config_data['state_type']}"
        )
        config_data["state_type"] = resolve_dotted_type(config_data["state_type"])

    try:
        return AgentConfig(**config_data)
    except Exception as e:
        logger.exception(f"[config_loader] Error: {e}")
        logger.error(f"Invalid AgentConfig: {e}")
        raise
