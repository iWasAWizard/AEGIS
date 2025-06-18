# aegis/tools/tool_metadata.py
from typing import Dict, Any

from pydantic import BaseModel

from aegis.exceptions import ToolNotFoundError
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


def load_tool_metadata(tool: Any) -> Dict[str, Any]:
    """Loads metadata from a tool's function attributes.

    This function inspects a tool function for special attributes set by the
    `@register_tool` decorator, such as `name`, `description`, `tags`, etc.
    It also generates a JSON schema for the tool's Pydantic input model.
    It provides a fallback mechanism to use the function's `__name__` and
    `__doc__` if the special attributes are not found.

    :param tool: The tool function object to inspect.
    :type tool: Any
    :return: A dictionary containing the structured metadata for the tool.
    :rtype: Dict[str, Any]
    """
    metadata = {}
    try:
        metadata["name"] = getattr(tool, "name", tool.__name__)
        metadata["description"] = getattr(
            tool, "description", tool.__doc__ or "No description"
        )
        metadata["tags"] = getattr(tool, "tags", ["uncategorized"])
        metadata["safe_mode"] = getattr(tool, "safe_mode", True)
        metadata["category"] = getattr(tool, "category", "wrapper")
        if hasattr(tool, "input_model") and issubclass(tool.input_model, BaseModel):
            metadata["input_schema"] = tool.input_model.model_json_schema()
        else:
            metadata["input_schema"] = {}
        logger.debug(f"Loaded tool-defined metadata for: {metadata['name']}")
    except Exception as e:
        logger.exception(
            f"Error loading metadata for tool {getattr(tool, '__name__', 'unknown')}: {e}"
        )
        metadata["name"] = getattr(tool, "__name__", "unnamed")
        metadata["description"] = tool.__doc__ or "No description"
        metadata["tags"] = ["fallback"]
        metadata["safe_mode"] = True
        metadata["category"] = "uncategorized"
        metadata["input_schema"] = {}
        logger.warning(f"Using fallback metadata for: {metadata['name']}")
    return metadata


def get_tool_metadata(tool_name: str, registry: Dict[str, Any]) -> Dict[str, Any]:
    """Extract metadata from a registered tool function and model.

    :param tool_name: Name of the tool to extract metadata for.
    :type tool_name: str
    :param registry: Tool registry dictionary.
    :type registry: Dict[str, Any]
    :return: ToolMetadata dictionary.
    :rtype: Dict[str, Any]
    :raises ToolNotFoundError: If the tool is not found in the registry.
    """
    tool = registry.get(tool_name)
    if not tool:
        logger.warning(f"[tool_metadata] No tool found in registry for: {tool_name}")
        raise ToolNotFoundError(f"Tool '{tool_name}' not found in registry.")
    return load_tool_metadata(tool)
