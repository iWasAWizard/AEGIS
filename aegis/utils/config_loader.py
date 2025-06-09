# aegis/utils/config_loader.py
"""
Config Loader

Loads agent configuration from raw dict, profile file, or preset.
"""

from pathlib import Path
from typing import Union, Optional

import yaml

from aegis.schemas.agent import AgentConfig
from aegis.utils.graph_profile_loader import load_agent_graph_config
from aegis.utils.logger import setup_logger
from aegis.utils.type_resolver import resolve_dotted_type
from aegis.utils.validation import validate_node_names


logger = setup_logger(__name__)


def load_agent_config(
    config_file: Optional[Union[str, Path]] = None,
    profile: Optional[str] = None,
    raw_config: Optional[dict] = None,
) -> AgentConfig:
    """
    Loads agent configuration from one of the supported sources and returns
    a full AgentConfig object containing both graph and runtime data.

    - profile name (YAML)
    - config file path
    - raw inline dictionary
    """
    config_data = {}

    if profile:
        try:
            logger.info(f"Loading config profile: {profile}")
            config_data = load_agent_graph_config(profile)
        except Exception as e:
            logger.exception(f"[config_loader] Error loading profile: {e}")
            raise

    elif config_file:
        try:
            logger.info(f"Loading config file: {config_file}")
            config_data = yaml.safe_load(Path(config_file).read_text())
        except Exception as e:
            logger.exception(f"[config_loader] Failed to load config file: {e}")
            raise

    elif raw_config is not None:
        logger.info("Using inline raw config dict")
        config_data = raw_config

    else:
        raise ValueError("Must provide either config_file, profile, or raw_config.")

    # Perform validation and type resolution before parsing
    if "state_type" in config_data and isinstance(config_data["state_type"], str):
        config_data["state_type"] = resolve_dotted_type(config_data["state_type"])

    validate_node_names(config_data)

    # Parse into the comprehensive AgentConfig and return it.
    return AgentConfig(**config_data)
