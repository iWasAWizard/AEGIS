# aegis/utils/config.py
"""
A simple utility for loading and accessing the central YAML configuration.
"""
from pathlib import Path

import yaml

_config = None


def get_config() -> dict:
    """Loads the config.yaml file and returns it as a dictionary.

    This function provides a singleton-like pattern for accessing global
    application settings defined in `config.yaml`. It reads the file from
    the project root on the first call and caches the result in memory for
    all subsequent calls to prevent redundant file I/O.

    :return: A dictionary containing the parsed YAML configuration.
    :rtype: dict
    :raises FileNotFoundError: If `config.yaml` is not found in the project root.
    """
    global _config
    if _config is None:
        config_path = Path("config.yaml")
        if not config_path.is_file():
            raise FileNotFoundError("Root config.yaml not found. Please create one.")
        with config_path.open("r") as f:
            _config = yaml.safe_load(f)
    return _config


def clear_config_cache():
    """Clears the in-memory cache for config.yaml."""
    global _config
    _config = None
