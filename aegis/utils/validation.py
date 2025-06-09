"""
Utility functions for validating and loading YAML-based preset and machine definitions.
"""

from typing import List

import yaml

from aegis.schemas.launch import LaunchRequest
from aegis.schemas.machine import MachineManifestCollection, MachineManifest
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


def load_presets(path: str) -> List[LaunchRequest]:
    """
    Load and validate a list of LaunchRequest presets from a YAML file.

    :param path: Filesystem path to the YAML file.
    :returns: List of parsed LaunchRequest objects.
    :raises Exception: If parsing or validation fails.
    """
    logger.info(f"[validation] Loading presets from: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    try:
        presets = [LaunchRequest(**entry) for entry in data]
        logger.info(f"[validation] Loaded {len(presets)} presets successfully.")
        return presets
    except Exception as e:
        logger.exception(f"[validation] Error: {e}")
        raise


def load_machine_manifest(path: str) -> List[MachineManifest]:
    """
    Load and validate a machine manifest YAML file as a list of entries.

    :param path: Path to the YAML file defining machine configurations.
    :returns: List of MachineManifest objects.
    :raises Exception: On YAML or schema failure.
    """
    logger.info(f"[validation] Loading machine manifest from: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    try:
        manifest_collection = MachineManifestCollection(machines=data.get("machines", []))
        logger.info(f"[validation] Loaded {len(manifest_collection.machines)} machines.")
        return manifest_collection.machines
    except Exception as e:
        logger.exception(f"[validation] Error: {e}")
        raise


def validate_node_names(config: dict):
    """
    Validates that all referenced node names exist in the node registry.

    :param config: Agent graph configuration loaded from YAML
    :type config: dict
    :raises ValueError: if a referenced node is not defined in the node list
    """
    logger.debug("🔍 Starting validate_node_names()")

    nodes = config.get("nodes", [])
    edges = config.get("edges", [])
    condition_map = config.get("condition_map", {})
    entrypoint = config.get("entrypoint", "")

    defined = {node["id"] for node in nodes}
    logger.debug(f"🧱 Defined nodes: {defined}")

    referenced = {entrypoint}
    logger.debug(f"🚪 Entry point: {entrypoint}")

    for src, dst in edges:
        logger.debug(f"🔗 Edge from '{src}' to '{dst}'")
        referenced.add(src)
        referenced.add(dst)

    logger.debug(f"🧩 Condition map values: {set(condition_map.values())}")
    referenced |= set(condition_map.values())

    logger.debug(f"🔎 Total referenced nodes (pre-validation): {referenced}")

    for node in referenced:
        if node == "__end__":
            logger.debug(f"✅ Skipping reserved node name: {node}")
            continue
        if node not in defined:
            logger.error(f"❌ Unknown node name in config: '{node}'")
            raise ValueError(f"Unknown node name in config: '{node}'")
        else:
            logger.debug(f"✅ Node '{node}' is valid")

    logger.info("✅ validate_node_names() completed without errors")
