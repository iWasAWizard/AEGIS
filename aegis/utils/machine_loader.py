# aegis/utils/machine_loader.py
"""
Utility for loading and resolving machine configurations from the manifest.
"""
from pathlib import Path

import yaml
from pydantic import ValidationError

from aegis.exceptions import ConfigurationError
from aegis.schemas.machine import MachineManifest
from aegis.schemas.settings import settings
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)

_machine_manifest_cache = None


def _load_manifest_from_file() -> dict:
    """Loads the machines.yaml file and caches it in memory.

    This function reads the `machines.yaml` file from the project root on its
    first call and stores the parsed content in a global cache to avoid
    repeated file I/O.

    :return: A dictionary representing the parsed content of the manifest file.
    :rtype: dict
    :raises ConfigurationError: If the file is not found or contains invalid YAML.
    """
    global _machine_manifest_cache
    if _machine_manifest_cache is None:
        manifest_path = Path("machines.yaml")
        if not manifest_path.is_file():
            raise ConfigurationError("machines.yaml not found in the root directory.")
        try:
            with manifest_path.open("r", encoding="utf-8") as f:
                _machine_manifest_cache = yaml.safe_load(f)
        except yaml.YAMLError as e:
            logger.exception("Failed to parse machines.yaml")
            raise ConfigurationError(f"Invalid YAML in machines.yaml: {e}") from e
    return _machine_manifest_cache


def get_machine(machine_name: str) -> MachineManifest:
    """Loads a specific machine's configuration from machines.yaml and resolves secrets.

    This function is the primary interface for accessing machine configurations. It
    performs the following steps:
    1. Loads the machine manifest (from cache if available).
    2. Finds the configuration for the specified `machine_name`.
    3. Resolves any secret placeholders (e.g., `${PASSWORD}`) using environment variables.
    4. Validates the final configuration against the `MachineManifest` schema.

    :param machine_name: The nickname of the machine to load.
    :type machine_name: str
    :return: A validated `MachineManifest` object with all secrets resolved.
    :rtype: MachineManifest
    :raises ConfigurationError: If the machine is not found, a secret is missing,
                                or the configuration is invalid.
    """
    manifest_data = _load_manifest_from_file()
    machine_config = manifest_data.get(machine_name)

    if not machine_config:
        raise ConfigurationError(
            f"Machine '{machine_name}' not found in machines.yaml."
        )

    # Resolve secret placeholders (e.g., ${ADMIN_PASSWORD})
    for key, value in machine_config.items():
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            secret_key = value[2:-1]  # Get the key name, e.g., ADMIN_PASSWORD
            secret_value = getattr(
                settings, secret_key.lower(), None
            )  # Use lower() for case-insensitivity
            if secret_value is None:
                raise ConfigurationError(
                    f"Secret '{secret_key}' for machine '{machine_name}' not found in environment or .env file."
                )
            machine_config[key] = secret_value

    try:
        return MachineManifest(**machine_config)
    except ValidationError as e:
        logger.error(f"Validation error for machine '{machine_name}': {e}")
        raise ConfigurationError(
            f"Invalid configuration for machine '{machine_name}': {e}"
        ) from e
