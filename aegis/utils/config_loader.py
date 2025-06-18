# aegis/utils/config_loader.py
"""
Config Loader for Agent Behavior.

This module provides the primary entry point for loading and validating an
agent's behavioral configuration from various sources, such as a preset
profile name, a direct file path, or a raw dictionary.
"""
import json
from pathlib import Path
from typing import Union, Optional

import yaml
from pydantic import ValidationError

from aegis.exceptions import ConfigurationError
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
    """Loads, validates, and resolves an agent configuration into a full AgentConfig object.

    This function serves as the central factory for agent configurations. It can
    load from a named preset in the `/presets` directory, a specific YAML file path,
    or a raw dictionary. It then performs several validation and resolution steps:
    1. Resolves any string-based type references (e.g., `state_type`) into actual Python classes.
    2. Validates that all referenced nodes in the graph structure are defined.
    3. Validates the final structure against the `AgentConfig` Pydantic model.

    :param config_file: Path to a specific YAML configuration file.
    :type config_file: Optional[Union[str, Path]]
    :param profile: The name of a preset profile in the 'presets/' directory.
    :type profile: Optional[str]
    :param raw_config: A raw dictionary containing the agent configuration.
    :type raw_config: Optional[dict]
    :return: A fully validated and resolved `AgentConfig` instance.
    :rtype: AgentConfig
    :raises ConfigurationError: If loading, parsing, or validation fails.
    :raises ValueError: If no configuration source is provided.
    """

    try:
        if profile:
            logger.info(f"Loading config from profile: '{profile}'")
            config_data = load_agent_graph_config(profile)
        elif config_file:
            logger.info(f"Loading config from file: '{config_file}'")
            config_data = yaml.safe_load(Path(config_file).read_text(encoding="utf-8"))
        elif raw_config is not None:
            logger.info("Loading from inline raw config dict.")
            config_data = raw_config
        else:
            raise ValueError("Must provide either config_file, profile, or raw_config.")

        if "state_type" in config_data and isinstance(config_data["state_type"], str):
            config_data["state_type"] = resolve_dotted_type(config_data["state_type"])

        validate_node_names(config_data)

        logger.debug(
            "Attempting to validate the following config data against AgentConfig:\n"
            f"{json.dumps(config_data, indent=2, default=str)}"
        )

        return AgentConfig(**config_data)

    except (
        FileNotFoundError,
        yaml.YAMLError,
        ValueError,
        ValidationError,
        ImportError,
    ) as e:
        logger.exception(f"Failed to load agent configuration: {e}")
        raise ConfigurationError(
            f"Failed to load or validate agent configuration. Reason: {e}"
        ) from e
