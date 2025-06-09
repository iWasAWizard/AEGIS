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

    :param profile_name: The name of the preset file (without .yaml extension).
    :type profile_name: str
    :return: The loaded configuration as a dictionary.
    :rtype: dict
    :raises FileNotFoundError: If the preset file does not exist.
    """
    presets_dir = Path("presets")
    profile_path = presets_dir / f"{profile_name}.yaml"
    if not profile_path.exists():
        raise FileNotFoundError(f"Preset profile '{profile_name}' does not exist.")

    config = yaml.safe_load(profile_path.read_text())
    return config
