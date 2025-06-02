"""
Utility functions for loading and validating schema-based YAML input.
"""

from typing import List

import yaml

from aegis.schemas.agent import PresetEntry
from aegis.schemas.machine import MachineManifest
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


def load_presets(path: str) -> List[PresetEntry]:
    """
    Load and validate a list of presets from a YAML file.
    """
    logger.info(f"[validation] Loading presets from: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    try:
        presets = [PresetEntry(**entry) for entry in data]
        logger.info(f"[validation] Loaded {len(presets)} presets successfully.")
        return presets
    except Exception as e:
        logger.exception(f"[validation] Error: {e}")
        logger.error(f"[validation] Failed to parse presets: {e}")
        raise


def load_machine_manifest(path: str) -> MachineManifest:
    """
    Load and validate a machine manifest YAML file.
    """
    logger.info(f"[validation] Loading machine manifest from: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    try:
        manifest = MachineManifest(machines=data)
        logger.info(f"[validation] Loaded {len(manifest.machines)} machines.")
        return manifest
    except Exception as e:
        logger.exception(f"[validation] Error: {e}")
        logger.error(f"[validation] Failed to parse machine manifest: {e}")
        raise
