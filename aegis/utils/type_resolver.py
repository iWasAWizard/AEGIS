"""Dynamically resolves and loads a Python class from a dotted string path.
Used to interpret types in configuration files."""

import importlib

from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


def resolve_dotted_type(dotted_path: str):
    """
    Given a dotted import path like 'aegis.agents.task_state.TaskState',
    dynamically import and return the type.
    """
    logger.debug(f"Resolving dotted path: {dotted_path}")

    module_path, _, class_name = dotted_path.rpartition(".")
    if not module_path or not class_name:
        logger.error(f"Invalid dotted path format: {dotted_path}")
        raise ValueError(f"Invalid dotted path: {dotted_path}")

    try:
        logger.debug(f"Importing module: {module_path}")
        module = importlib.import_module(module_path)
        resolved = getattr(module, class_name)
        logger.debug(f"Resolved '{dotted_path}' to: {resolved}")
        return resolved
    except (ImportError, AttributeError) as e:
        logger.exception(f"Unable to resolve type from '{dotted_path}': {e}")
        raise ImportError(f"Unable to resolve type from '{dotted_path}': {e}") from e
