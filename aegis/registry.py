"""Provides centralized tool registration, validation, and lookup.
All tools must be registered via this interface to be discoverable and callable by agents.
"""

import os
import importlib
import pathlib

from typing import Any, Callable, Dict, List, Optional, Type

from dotenv import load_dotenv
from pydantic import BaseModel, create_model

from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)
load_dotenv()

# these are holdover
KNOWN_TAGS = {
    "network",
    "filesystem",
    "system",
    "integration",
    "llm",
    "sensor",
    "utility",
    "action",
    "random",
    "mock",
    "fuzz",
    "integer",
    "boolean",
    "choice",
    "string",
    "corrupt",
    "test",
    "chaos",
    "dev",
    "file",
    "primitive",
    "remote",
    "local",
}
KNOWN_CATEGORIES = {"primitive", "wrapper", "composite", "internal"}
# holdover stops here


class ToolEntry(BaseModel):
    """Represents a registered tool within the agent system.

    Stores metadata, execution logic, input validation, and configuration
    for tools exposed to the agent runtime.
    """

    name: str
    run: Callable[[BaseModel], Any]
    input_model: Type[BaseModel]
    tags: List[str]
    description: str
    safe_mode: bool = True
    purpose: Optional[str] = None
    category: Optional[str] = None
    timeout: Optional[int] = None
    retries: int = 0


TOOL_REGISTRY: Dict[str, ToolEntry] = {}


def normalize_tags(tags: List[str]) -> List[str]:
    """Normalize and deduplicate tags by converting them to lowercase and stripping whitespace.

    :param tags: List of tag strings.
    :return: Normalized and sorted list of unique tags.
    """
    return sorted(set((tag.lower().strip() for tag in tags)))


def validate_input_model(model: Type[BaseModel]) -> None:
    """Validate that a given Pydantic model can be used for tool input.

    :param model: The Pydantic model class to validate.
    :raises TypeError: If the model is invalid or non-instantiable.
    """
    try:
        create_model("ValidationCheck", __base__=model)
    except Exception as e:
        raise TypeError(
            f"Input model '{model.__name__}' is invalid or non-instantiable: {e}"
        )


def validate_tags_and_category(tags: List[str], category: Optional[str]):
    """Ensure all tags and category values are recognized.

    :param tags: List of tags to validate.
    :param category: Optional category to validate.
    :raises ValueError: If any tag or category is invalid.
    """
    for tag in tags:
        if tag not in KNOWN_TAGS:
            raise ValueError(
                f"Invalid tag '{tag}'. Must be one of: {', '.join(sorted(KNOWN_TAGS))}"
            )
    if category and category not in KNOWN_CATEGORIES:
        raise ValueError(
            f"Invalid category '{category}'. Must be one of: {', '.join(sorted(KNOWN_CATEGORIES))}"
        )


def register_tool(
    name: str,
    input_model: Type[BaseModel],
    tags: List[str],
    description: str,
    safe_mode: bool = True,
    purpose: Optional[str] = None,
    category: Optional[str] = None,
    timeout: Optional[int] = None,
    retries: int = 0,
) -> Callable[[Callable[[BaseModel], Any]], Callable[[BaseModel], Any]]:
    """Register a tool for use within the agent system.

    Performs validation, metadata registration, and adds it to the global registry.

    :param name: Unique name of the tool.
    :param input_model: Pydantic model used to validate tool input.
    :param tags: Tags for categorization and filtering.
    :param description: Human-readable description of the tool.
    :param safe_mode: Whether the tool can be used in restricted environments.
    :param purpose: Optional extended purpose description.
    :param category: Tool classification (e.g., primitive, wrapper).
    :param timeout: Optional max run time in seconds.
    :param retries: Number of times to retry on failure.
    :return: Decorator that registers the function as a tool.
    """

    def decorator(func: Callable[[BaseModel], Any]) -> Callable[[BaseModel], Any]:
        """A decorator used to tag and register tools in the system's tool registry."""
        if not callable(func):
            raise TypeError(f"Registered tool '{name}' is not callable.")
        if name in TOOL_REGISTRY:
            raise ValueError(
                f"Tool '{name}' is already registered. Duplicate names are not allowed."
            )
        validate_input_model(input_model)
        normalized_tags = normalize_tags(tags)
        # validate_tags_and_category(normalized_tags, category)
        entry = ToolEntry(
            name=name,
            run=func,
            input_model=input_model,
            tags=normalized_tags,
            description=description,
            safe_mode=safe_mode,
            purpose=purpose,
            category=category,
            timeout=timeout,
            retries=retries,
        )
        TOOL_REGISTRY[name] = entry
        logger.info(
            f"Registered tool: {name} | "
            f"Tags: {normalized_tags} | "
            f"Profile: {os.getenv('DEFAULT_PROFILE', 'default')} | "
            f"Category: {category or 'N/A'}"
        )
        return func

    return decorator


def get_tool(name: str, safe_mode: bool = True) -> Optional[ToolEntry]:
    """Retrieve a registered tool by name, optionally filtering by safe mode.

    :param name: Name of the tool to retrieve.
    :param safe_mode: Whether to restrict results to safe tools.
    :return: ToolEntry object or None if not found or unsafe.
    """
    tool = TOOL_REGISTRY.get(name)
    if tool is None:
        logger.warning(f"Requested tool '{name}' not found in registry.")
        return None
    if safe_mode and (not tool.safe_mode):
        logger.warning(f"Tool '{name}' is not available in safe_mode.")
        return None
    return tool


def list_tools(safe_mode: bool = True) -> List[str]:
    """List all registered tool names, optionally filtering by safe mode.

    :param safe_mode: If True, exclude tools not marked safe.
    :return: List of tool names.
    """
    return [
        name for name, tool in TOOL_REGISTRY.items() if not safe_mode or tool.safe_mode
    ]


def log_registry_contents():
    """Output all currently registered tools and their metadata to the logger.

    Useful for debugging and verification of the tool registry state.
    """
    logger.info("Registered Tools:")
    for name, tool in TOOL_REGISTRY.items():
        logger.info(
            f"- {name}"
            f"  Tags: {tool.tags}"
            f"  Input: {tool.input_model.__name__}"
            f"  Safe: {tool.safe_mode}"
            f"  Timeout: {tool.timeout}"
            f"  Retries: {tool.retries}"
            f"  Description: {tool.description}"
            f"  Purpose: {tool.purpose or 'N/A'}"
            f"  Category: {tool.category or 'N/A'}"
        )
