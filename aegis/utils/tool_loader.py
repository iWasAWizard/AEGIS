# aegis/utils/tool_loader.py
"""
Tool Loader Utilities.

Provides dynamic discovery and import of tool modules from the core `aegis/tools`
directory and a user-extensible top-level `plugins` directory. Calling
`import_all_tools()` once at runtime ensures all tools decorated with
`@register_tool` are available in the central `TOOL_REGISTRY`.
"""

import importlib
import os
import pathlib
import sys

from aegis.registry import TOOL_REGISTRY
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)
logger.debug("Initializing aegis.utils.tool_loader module...")


def _import_from_directory(base_dir: pathlib.Path, base_package_name: str):
    """
    Helper function to recursively import Python modules from a given directory.

    This function scans a directory for `.py` files, converts their file paths
    into Python module paths, and then imports them. This process triggers the
    `@register_tool` decorator within each file, populating the global registry.

    :param base_dir: The absolute path to the directory to scan.
    :type base_dir: pathlib.Path
    :param base_package_name: The corresponding Python package name for the directory.
    :type base_package_name: str
    """
    if not base_dir.is_dir():
        logger.warning(f"Tool directory '{base_dir}' does not exist. Skipping.")
        return
    elif base_package_name is None:
        logger.info("No base package name provided!")

    logger.info(f"Scanning for tools in directory: {base_dir}")
    if str(base_dir.parent) not in sys.path:
        sys.path.insert(0, str(base_dir.parent))

    for path in base_dir.rglob("*.py"):
        if "__init__" in path.name:
            continue

        rel_path = path.relative_to(base_dir.parent)
        # Use os.sep for cross-platform compatibility
        module_path = str(rel_path.with_suffix("")).replace(os.sep, ".")

        try:
            importlib.import_module(module_path)
            logger.debug(f"Successfully imported tool module: {module_path}")
        except Exception as e:
            logger.error(f"Failed to import tool module {module_path}. Error: {e}")


def import_all_tools():
    """Recursively imports all Python modules from the core tools directory
    and the user-defined plugins directory to register them.

    This function must be called once at application startup to ensure all
    agent capabilities are available.
    """
    # Clear the registry to make this function idempotent. This prevents issues
    # with hot-reloading where modules might be imported multiple times.
    TOOL_REGISTRY.clear()
    logger.info("--- Starting Dynamic Tool Import (Registry Cleared) ---")

    core_tools_dir = pathlib.Path(__file__).parent.parent / "tools"
    _import_from_directory(core_tools_dir, "aegis.tools")

    project_root = pathlib.Path.cwd()
    plugins_dir = project_root / "plugins"
    if plugins_dir.exists():
        _import_from_directory(plugins_dir, "plugins")
    else:
        logger.info("No 'plugins' directory found. Skipping plugin loading.")

    logger.info("--- Dynamic Tool Import Complete ---")
