# aegis/utils/tool_loader.py
"""
Tool Loader Utilities.

Provides dynamic discovery and import of tool modules from the core `aegis/tools`
directory and a user-extensible top-level `plugins` directory. Calling
`import_all_tools()` once at runtime ensures all tools decorated with
`@register_tool` are available in the central `TOOL_REGISTRY`.
"""

import importlib
import pathlib
import sys

from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


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

    logger.info(f"Scanning for tools in directory: {base_dir}")
    # Add the parent of the package to the system path to allow direct import
    if str(base_dir.parent) not in sys.path:
        sys.path.insert(0, str(base_dir.parent))

    for path in base_dir.rglob("*.py"):
        if "__init__" in path.name:
            continue

        # Convert filesystem path to a Python module path
        # e.g., /path/to/project/aegis/tools/primitives/chaos.py -> "aegis.tools.primitives.chaos"
        rel_path = path.relative_to(base_dir.parent)
        module_path = str(rel_path.with_suffix("")).replace(pathlib.os.sep, ".")

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
    logger.info("--- Starting Dynamic Tool Import ---")

    # 1. Import core tools from `aegis/tools`
    core_tools_dir = pathlib.Path(__file__).parent.parent / "tools"
    _import_from_directory(core_tools_dir, "aegis.tools")

    # 2. Import user-defined plugin tools from `plugins/` at the project root
    project_root = pathlib.Path(__file__).parent.parent.parent
    plugins_dir = project_root / "plugins"
    _import_from_directory(plugins_dir, "plugins")

    logger.info("--- Dynamic Tool Import Complete ---")
