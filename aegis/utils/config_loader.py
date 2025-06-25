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
from aegis.utils.config import get_config as get_system_config
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

    This function serves as the central factory for agent configurations. It merges
    configurations from multiple sources with a clear precedence:
    System Defaults (from config.yaml) < Preset Config < Raw/File Config.

    :param config_file: Path to a specific YAML configuration file.
    :param profile: The name of a preset profile in the 'presets/' directory.
    :param raw_config: A raw dictionary containing the agent configuration.
    :return: A fully validated and resolved `AgentConfig` instance.
    :raises ConfigurationError: If loading, parsing, or validation fails.
    """
    try:
        # 1. Start with system-wide defaults from config.yaml
        system_defaults = get_system_config().get("defaults", {})
        merged_config = system_defaults.copy()
        
        # 2. Load preset and merge its settings
        preset_data = {}
        if profile:
            logger.info(f"Loading config from profile: '{profile}'")
            preset_data = load_agent_graph_config(profile)
            # Merge runtime settings from preset
            if "runtime" in preset_data:
                merged_config.update(preset_data["runtime"])
        
        # 3. Load from file or raw dict and merge on top
        final_config_data = {}
        if config_file:
            logger.info(f"Loading config from file: '{config_file}'")
            final_config_data = yaml.safe_load(Path(config_file).read_text(encoding="utf-8"))
        elif raw_config:
            logger.info("Loading from inline raw config dict.")
            final_config_data = raw_config

        # Merge the highest-precedence runtime settings
        if "runtime" in final_config_data:
             merged_config.update(final_config_data["runtime"])

        # Construct the final config object
        # Graph structure comes from preset or file/raw, runtime comes from merged data
        graph_structure_source = final_config_data or preset_data
        
        # Ensure 'runtime' key exists before assigning to it
        if "runtime" not in graph_structure_source:
             graph_structure_source["runtime"] = {}
        graph_structure_source["runtime"] = merged_config

        if "state_type" in graph_structure_source and isinstance(graph_structure_source["state_type"], str):
            graph_structure_source["state_type"] = resolve_dotted_type(graph_structure_source["state_type"])

        validate_node_names(graph_structure_source)

        logger.debug(
            "Attempting to validate the final merged config:\n"
            f"{json.dumps(graph_structure_source, indent=2, default=str)}"
        )
        return AgentConfig(**graph_structure_source)

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