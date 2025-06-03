"""
Tool Loader Utilities.

Provides dynamic discovery and import of tool modules under aegis/tools.
Call `import_all_tools()` once at runtime to ensure all tools decorated
with @register_tool are registered in TOOL_REGISTRY.
"""

import importlib
import pathlib
import traceback

from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


def import_all_tools():
    """
    Recursively imports all Python modules under aegis.tools.

    This is required to ensure that any tools decorated with
    @register_tool are actually executed and registered.

    Should be called exactly once at startup, before using list_tools(), get_tool(), etc.
    """
    base_package = "aegis.tools"
    base_dir = pathlib.Path(__file__).parent.parent / "tools"

    if not base_dir.exists():
        logger.warning("Tool directory %s does not exist.", base_dir)
        return

    for path in base_dir.rglob("*.py"):
        if "__" in path.name:
            continue  # Skip __init__.py and __pycache__

        rel_path = path.relative_to(base_dir).with_suffix("")
        module_path = f"{base_package}.{str(rel_path).replace('/', '.').replace('\\', '.')}"

        try:
            importlib.import_module(module_path)
            logger.debug("Imported tool module: %s", module_path)
        except Exception as e:
            logger.warning("Failed to import tool module %s", module_path)
            logger.debug("Traceback for %s:\n%s", module_path, traceback.format_exc())