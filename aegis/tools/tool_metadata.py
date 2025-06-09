from typing import Dict, Any

from pydantic import BaseModel

from aegis.exceptions import ToolNotFoundError
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


def load_tool_metadata(tool: Any) -> Dict[str, Any]:
    # ... (function content is unchanged)
    metadata = {}
    try:
        metadata["name"] = getattr(tool, "name", tool.__name__)
        metadata["description"] = getattr(tool, "description", tool.__doc__ or "No description")
        metadata["tags"] = getattr(tool, "tags", ["uncategorized"])
        metadata["safe_mode"] = getattr(tool, "safe_mode", True)
        metadata["category"] = getattr(tool, "category", "wrapper")
        if hasattr(tool, "input_model") and issubclass(tool.input_model, BaseModel):
            metadata["input_schema"] = tool.input_model.model_json_schema()
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


def get_tool_metadata(
        tool_name: str, registry: Dict[str, Any]
) -> Dict[str, Any]:
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
