from typing import Dict, Any, Optional

from pydantic import BaseModel

from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


def load_tool_metadata(tool: Any) -> Dict[str, Any]:
    """
    Attempt to extract metadata from a tool object.
    If missing, fallback to its docstring and default assumptions.

    :param tool: Callable or tool entry
    :type tool: Any
    :return: Metadata dictionary
    :rtype: Dict[str, Any]
    """
    metadata = {}
    try:
        metadata["name"] = getattr(tool, "name", tool.__name__)
        metadata["description"] = getattr(tool, "description", tool.__doc__ or "No description")
        metadata["tags"] = getattr(tool, "tags", ["uncategorized"])
        metadata["safe_mode"] = getattr(tool, "safe_mode", True)
        metadata["category"] = getattr(tool, "category", "wrapper")

        if hasattr(tool, "input_model") and issubclass(tool.input_model, BaseModel):
            metadata["input_schema"] = tool.input_model.schema()
        else:
            metadata["input_schema"] = {}

        logger.info(f"[tool_metadata] Using tool-defined metadata for: {metadata['name']}")
    except Exception as e:
        logger.exception(f"[tool_metadata] Error: {e}")
        metadata["name"] = getattr(tool, "__name__", "unnamed")
        metadata["description"] = tool.__doc__ or "No description"
        metadata["tags"] = ["fallback"]
        metadata["safe_mode"] = True
        metadata["category"] = "uncategorized"
        metadata["input_schema"] = {}

        logger.info(f"[tool_metadata] Using fallback metadata for: {metadata['name']}")
    return metadata


def get_tool_metadata(tool_name: str, registry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extract metadata from a registered tool function and model.

    :param tool_name: Name of the tool to extract metadata for
    :type tool_name: str
    :param registry: Tool registry dictionary
    :type registry: Dict[str, Any]
    :return: ToolMetadata dictionary or None
    :rtype: Optional[Dict[str, Any]]
    """
    tool = registry.get(tool_name)
    if not tool:
        logger.warning(f"[tool_metadata] No tool found in registry for: {tool_name}")
        return None
    return load_tool_metadata(tool)
