"""
Executes a registered tool using input parameters and enforces timeout, retries, and logging.
"""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

from aegis.registry import get_tool, ToolEntry
from aegis.utils.logger import setup_logger
from aegis.agents.task_state import TaskState

logger = setup_logger(__name__)


async def execute_tool(state: TaskState) -> TaskState:
    """
    Retrieves the tool and executes it with the planned arguments.

    :param state: Task execution state
    :type state: TaskState
    :return: Updated task state with execution result
    :rtype: TaskState
    """
    if not state.tool_name:
        raise ValueError("Tool name missing from state. Plan step may have failed.")

    tool = get_tool(state.tool_name)
    if not tool:
        raise ValueError(
            f"Tool '{state.tool_name}' not found or not allowed in safe_mode."
        )

    logger.info(f"[execute_tool] Running tool: {tool.name}")
    input_data = tool.input_model(**state.steps_output["plan"]["tool_args"])
    result = await execute_tool_with_timing(tool, input_data)
    state.steps_output["tool_result"] = result
    return state


async def execute_tool_with_timing(tool: ToolEntry, input_data) -> any:
    """
    Handles execution timing, retries, and concurrency.

    :param tool: Tool entry with metadata and run method
    :type tool: ToolEntry
    :param input_data: Parsed tool arguments as a pydantic model
    :type input_data: BaseModel
    :return: Tool output result
    :rtype: Any
    """
    retries = tool.retries
    timeout = tool.timeout
    attempt = 0

    while attempt <= retries:
        attempt += 1
        try:
            logger.info(
                f"[tool] Executing '{tool.name}' (attempt {attempt}/{retries + 1})"
            )
            logger.debug(f"[tool] Input data: {input_data.model_dump_json(indent=2)}")
            start = time.perf_counter()

            if asyncio.iscoroutinefunction(tool.run):
                result = (
                    await asyncio.wait_for(tool.run(input_data), timeout=timeout)
                    if timeout
                    else await tool.run(input_data)
                )
            else:
                loop = asyncio.get_running_loop()
                with ThreadPoolExecutor() as pool:
                    result = (
                        await asyncio.wait_for(
                            loop.run_in_executor(pool, tool.run, input_data),
                            timeout=timeout,
                        )
                        if timeout
                        else await loop.run_in_executor(pool, tool.run, input_data)
                    )

            elapsed = time.perf_counter() - start
            logger.info(f"[tool] '{tool.name}' completed in {elapsed:.2f}s")
            logger.debug(f"[tool] Result preview: {str(result)[:400]}")
            return result

        except Exception as e:
            logger.exception(f"[tool] Execution error on attempt {attempt}: {e}")
            if attempt > retries:
                logger.error(
                    f"[tool] '{tool.name}' failed after {retries + 1} attempts."
                )
                raise
