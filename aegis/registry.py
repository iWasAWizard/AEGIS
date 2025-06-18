# aegis/registry.py
"""Provides centralized tool registration, validation, and lookup.

This module is the single source of truth for all tools available to the AEGIS
agent. It uses a decorator-based system to register functions, validate their
metadata and input schemas, and make them discoverable at runtime. All tools
must be registered via this interface to be callable by the agent.
"""

from typing import Any, Callable, Dict, List, Optional, Type

from dotenv import load_dotenv
from pydantic import BaseModel, create_model

from aegis.exceptions import ToolNotFoundError, ToolValidationError
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)
load_dotenv()
logger.info("Initializing aegis.registry module...")


class ToolEntry(BaseModel):
    """Represents a registered tool within the agent system.

    This class stores the complete, validated metadata for a single tool,
    including its execution logic, input validation model, and descriptive
    properties used for planning and filtering.

    :ivar name: The unique, callable name of the tool.
    :vartype name: str
    :ivar run: The actual function to execute for this tool.
    :vartype run: Callable[[Any], Any]
    :ivar input_model: The Pydantic model used to validate the tool's input.
    :vartype input_model: Type[BaseModel]
    :ivar tags: A list of lowercase tags for categorization and filtering.
    :vartype tags: List[str]
    :ivar description: A human-readable summary of what the tool does.
    :vartype description: str
    :ivar safe_mode: A boolean indicating if the tool can perform dangerous actions.
    :vartype safe_mode: bool
    :ivar purpose: An optional, concise verb describing the tool's main action.
    :vartype purpose: Optional[str]
    :ivar category: An optional high-level category (e.g., 'primitive', 'wrapper').
    :vartype category: Optional[str]
    :ivar timeout: An optional execution timeout in seconds for the tool.
    :vartype timeout: Optional[int]
    :ivar retries: The number of times to retry the tool on failure.
    :vartype retries: int
    """

    name: str
    run: Callable[[Any], Any]  # The input is a Pydantic model instance
    input_model: Type[BaseModel]
    tags: List[str]
    description: str
    safe_mode: bool = True
    purpose: Optional[str] = None
    category: Optional[str] = None
    timeout: Optional[int] = None
    retries: int = 0

    class Config:
        """Pydantic configuration to allow arbitrary types like callables."""

        arbitrary_types_allowed = True


TOOL_REGISTRY: Dict[str, ToolEntry] = {}


def normalize_tags(tags: List[str]) -> List[str]:
    """Normalize and deduplicate tags by converting to lowercase and stripping whitespace.

    :param tags: A list of tag strings.
    :type tags: List[str]
    :return: A normalized and sorted list of unique tags.
    :rtype: List[str]
    """
    return sorted({tag.lower().strip() for tag in tags})


def validate_input_model(model: Type[BaseModel]) -> None:
    """Validate that a given Pydantic model can be used for tool input.

    :param model: The Pydantic model class to validate.
    :type model: Type[BaseModel]
    :raises ToolValidationError: If the model is invalid or cannot be instantiated.
    """
    try:
        # Check if it's a valid Pydantic model in the first place
        if not issubclass(model, BaseModel):
            raise TypeError("Input model must be a subclass of pydantic.BaseModel.")
        create_model("ValidationCheck", __base__=model)
    except Exception as e:
        raise ToolValidationError(
            f"Input model '{model.__name__}' is invalid or non-instantiable: {e}"
        ) from e


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
) -> Callable[[Callable[[Any], Any]], Callable[[Any], Any]]:
    """A decorator to register a function as a tool for the agent system.

    This decorator is the primary mechanism for adding new capabilities to the agent.
    It attaches essential metadata to a function and adds it to the global
    `TOOL_REGISTRY`, making it discoverable and callable by the agent's planner.

    :param name: The unique, callable name for the tool.
    :type name: str
    :param input_model: The Pydantic model for validating the tool's input.
    :type input_model: Type[BaseModel]
    :param tags: A list of tags for categorizing and filtering the tool.
    :type tags: List[str]
    :param description: A human-readable description of the tool's purpose.
    :type description: str
    :param safe_mode: If True, the tool is considered safe from performing destructive actions. Defaults to True.
    :type safe_mode: bool
    :param purpose: An optional, concise verb describing the tool's action.
    :type purpose: Optional[str]
    :param category: An optional high-level category (e.g., 'primitive', 'wrapper').
    :type category: Optional[str]
    :param timeout: An optional execution timeout in seconds.
    :type timeout: Optional[int]
    :param retries: The number of times to retry the tool on failure. Defaults to 0.
    :type retries: int
    :return: A decorator that registers the function.
    :rtype: Callable
    """

    def decorator(func: Callable[[Any], Any]) -> Callable[[Any], Any]:
        if not callable(func):
            raise TypeError(f"Registered tool '{name}' must be a callable function.")
        if name in TOOL_REGISTRY:
            logger.warning(
                f"A tool with the name '{name}' is already registered. Overwriting."
            )

        validate_input_model(input_model)
        normalized_tags = normalize_tags(tags)

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
        logger.debug(
            f"Registered tool: {name} | "
            f"Category: {category or 'N/A'} | "
            f"Safe: {safe_mode}"
        )
        return func

    return decorator


def get_tool(name: str, safe_mode: bool = True) -> ToolEntry:
    """Retrieve a registered tool by name, optionally filtering by safe mode.

    :param name: The name of the tool to retrieve.
    :type name: str
    :param safe_mode: If True, only return the tool if it is marked as safe.
    :type safe_mode: bool
    :return: A ToolEntry object if the tool is found and meets criteria.
    :rtype: ToolEntry
    :raises ToolNotFoundError: If the tool is not in the registry or is blocked by safe mode.
    """
    tool = TOOL_REGISTRY.get(name)
    if tool is None:
        logger.warning(f"Requested tool '{name}' not found in registry.")
        raise ToolNotFoundError(
            f"Tool '{name}' not found in registry. Please ensure it is spelled correctly and registered."
        )
    if safe_mode and not tool.safe_mode:
        logger.warning(
            f"Tool '{name}' is not available in safe_mode, but safe_mode is active."
        )
        raise ToolNotFoundError(f"Tool '{name}' is blocked by safe mode.")
    return tool


def list_tools(safe_mode: bool = True) -> List[str]:
    """List the names of all available tools, optionally filtering by safe mode.

    :param safe_mode: If True, only include tools marked as safe in the list.
    :type safe_mode: bool
    :return: A list of tool names.
    :rtype: List[str]
    """
    return [
        name for name, tool in TOOL_REGISTRY.items() if not safe_mode or tool.safe_mode
    ]


def log_registry_contents() -> None:
    """Outputs all currently registered tools and their metadata to the logger."""
    logger.info("--- Tool Registry Contents ---")
    if not TOOL_REGISTRY:
        logger.info("Registry is empty.")
        return

    for name, tool in sorted(TOOL_REGISTRY.items()):
        logger.info(
            f"- Tool: {name}\n"
            f"  - Description: {tool.description}\n"
            f"  - Category: {tool.category or 'N/A'}\n"
            f"  - Tags: {tool.tags}\n"
            f"  - Input Model: {tool.input_model.__name__}\n"
            f"  - Safe: {tool.safe_mode}"
        )
    logger.info(f"--- End of Registry Contents ({len(TOOL_REGISTRY)} tools) ---")
