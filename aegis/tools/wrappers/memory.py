# aegis/tools/wrappers/memory.py
"""
Tools for providing the agent with a persistent, long-term key-value memory.

This allows the agent to store and recall specific facts, preferences, or
intermediate results across different tasks, simulating a "notebook" or
a simple database.
"""
from pydantic import BaseModel, Field

from aegis.exceptions import ToolExecutionError
from aegis.executors.redis_exec import RedisExecutor
from aegis.registry import register_tool
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


# --- Input Models ---


class SaveToMemoryInput(BaseModel):
    """Input for saving a key-value pair to the agent's long-term memory.

    :ivar key: The unique key under which to store the value.
    :vartype key: str
    :ivar value: The string value to store.
    :vartype value: str
    """

    key: str = Field(..., description="The unique key under which to store the value.")
    value: str = Field(..., description="The string value to store.")


class RecallFromMemoryInput(BaseModel):
    """Input for recalling a value from the agent's long-term memory.

    :ivar key: The unique key of the value to retrieve.
    :vartype key: str
    """

    key: str = Field(..., description="The unique key of the value to retrieve.")


# --- Tools ---


@register_tool(
    name="save_to_memory",
    input_model=SaveToMemoryInput,
    description="Saves a key-value pair to the agent's persistent long-term memory for later recall.",
    category="memory",
    tags=["memory", "internal", "redis", "wrapper"],
    safe_mode=True,
    purpose="Store a specific fact or piece of data for future use.",
)
def save_to_memory(input_data: SaveToMemoryInput) -> str:
    """
    Uses the RedisExecutor to store a key-value pair. This acts as the agent's
    long-term, explicit memory.

    :param input_data: The key and value to store.
    :type input_data: SaveToMemoryInput
    :return: A confirmation message of the save operation.
    :rtype: str
    :raises ToolExecutionError: If the Redis service is unavailable or the operation fails.
    """
    try:
        executor = RedisExecutor()
        return executor.set_value(input_data.key, input_data.value)
    except Exception as e:
        # Catch exceptions from executor instantiation or method call
        logger.exception(f"Tool 'save_to_memory' failed for key '{input_data.key}'.")
        raise ToolExecutionError(f"Failed to save to memory: {e}")


@register_tool(
    name="recall_from_memory",
    input_model=RecallFromMemoryInput,
    description="Recalls a value from the agent's persistent long-term memory using its key.",
    category="memory",
    tags=["memory", "internal", "redis", "wrapper"],
    safe_mode=True,
    purpose="Retrieve a specific fact or piece of data that was previously stored.",
)
def recall_from_memory(input_data: RecallFromMemoryInput) -> str:
    """
    Uses the RedisExecutor to retrieve a value by its key from the agent's
    long-term, explicit memory.

    :param input_data: The key of the value to recall.
    :type input_data: RecallFromMemoryInput
    :return: The retrieved value, or a message indicating the key was not found.
    :rtype: str
    :raises ToolExecutionError: If the Redis service is unavailable or the operation fails.
    """
    try:
        executor = RedisExecutor()
        return executor.get_value(input_data.key)
    except Exception as e:
        # Catch exceptions from executor instantiation or method call
        logger.exception(
            f"Tool 'recall_from_memory' failed for key '{input_data.key}'."
        )
        raise ToolExecutionError(f"Failed to recall from memory: {e}")
