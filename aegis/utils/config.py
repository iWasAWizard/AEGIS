# aegis/utils/config.py
"""
A simple utility for loading and accessing the central YAML configuration.
"""
from pathlib import Path
import yaml

_config = None


def get_config() -> dict:
    """Loads the config.yaml file and returns it as a dictionary.

    Caches the config in memory after the first read.
    """
    global _config
    if _config is None:
        config_path = Path("config.yaml")
        if not config_path.is_file():
            raise FileNotFoundError("Root config.yaml not found. Please create one.")
        with config_path.open("r") as f:
            _config = yaml.safe_load(f)
    return _config
