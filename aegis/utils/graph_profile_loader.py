# aegis/utils/graph_profile_loader.py
"""
Graph loader for parsing AgentGraphConfig from a preset profile.
"""

from pathlib import Path

import yaml

from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


def load_agent_graph_config(profile_name: str) -> dict:
    """
    Loads a preset profile from the /presets directory and returns it as a
    raw dictionary, without validation.

    This utility is a low-level loader specifically for named presets. It constructs
    the expected file path within the `presets/` directory and parses the YAML content.
    Higher-level functions like `load_agent_config` are responsible for validation.

    :param profile_name: The name of the preset file (without .yaml extension).
    :type profile_name: str
    :return: The loaded configuration as a dictionary.
    :rtype: dict
    :raises FileNotFoundError: If the preset file does not exist.
    :raises yaml.YAMLError: If the file content is not valid YAML.
    """
    presets_dir = Path("presets")
    profile_path = presets_dir / f"{profile_name}.yaml"
    if not profile_path.exists():
        raise FileNotFoundError(f"Preset profile '{profile_name}' does not exist at '{profile_path}'.")

    config = yaml.safe_load(profile_path.read_text())
    return config
