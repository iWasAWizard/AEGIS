# aegis/utils/type_resolver.py
"""Dynamically resolves and loads a Python class from a dotted string path.

This utility is crucial for allowing configurations (e.g., in YAML files) to
specify Python types as strings, which can then be resolved into actual
class objects at runtime. This is primarily used for loading the `TaskState`
class for an agent graph.
"""

import importlib

from aegis.exceptions import ConfigurationError
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


def resolve_dotted_type(dotted_path: str):
    """Given a dotted import path, dynamically import and return the type.

    For example, given the string 'aegis.agents.task_state.TaskState', this
    function will import the `aegis.agents.task_state` module and return
    the `TaskState` class object from it.

    :param dotted_path: The dotted path string.
    :type dotted_path: str
    :return: The resolved class or function object.
    :rtype: Any
    :raises ConfigurationError: If the path is invalid or the type cannot be resolved.
    """
    logger.debug(f"Resolving dotted path: {dotted_path}")

    module_path, _, class_name = dotted_path.rpartition(".")
    if not module_path or not class_name:
        logger.error(f"Invalid dotted path format: {dotted_path}")
        raise ConfigurationError(f"Invalid dotted path format: '{dotted_path}'")

    try:
        module = importlib.import_module(module_path)
        resolved_type = getattr(module, class_name)
        logger.debug(f"Resolved '{dotted_path}' to: {resolved_type}")
        return resolved_type
    except (ImportError, AttributeError) as e:
        logger.exception(f"Unable to resolve type from '{dotted_path}': {e}")
        raise ConfigurationError(
            f"Unable to resolve type from '{dotted_path}': {e}"
        ) from e
