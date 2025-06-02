"""Executes a registered tool using input parameters and enforces timeout, retries, and logging."""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

from aegis.registry import get_tool, ToolEntry
from aegis.utils.logger import setup_logger

"\nExecutes a registered tool using input parameters and enforces timeout, retries, and logging.\n"
logger = setup_logger(__name__)


async def route_execution(state):
    """
    route_execution.
    :param state: Description of state
    :type state: Any
    :return: Description of return value
    :rtype: Any
    """
    tool = get_tool(state.tool_name)
    if not state.tool_name:
        raise ValueError("Tool name missing from state. Plan step may have failed.")
    elif not tool:
        raise ValueError(
            f"Tool '{state.tool_name}' not found or not allowed in safe_mode."
        )
    input_data = tool.input_model(**state.tool_request)
    return await execute_tool_with_timing(tool, input_data)


async def execute_tool_with_timing(tool: ToolEntry, input_data):
    """
    execute_tool_with_timing.
    :param tool: Description of tool
    :param input_data: Description of input_data
    :type tool: Any
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    retries = tool.retries
    timeout = tool.timeout
    attempt = 0
    while True:
        try:
            attempt += 1
            logger.info(
                f"[tool] Executing '{tool.name}' (attempt {attempt}/{retries + 1})"
            )
            logger.debug(f"[tool] Input data: {input_data.model_dump_json(indent=2)}")
            start = time.perf_counter()
            if asyncio.iscoroutinefunction(tool.run):
                if timeout:
                    result = await asyncio.wait_for(
                        tool.run(input_data), timeout=timeout
                    )
                else:
                    result = await tool.run(input_data)
            else:
                loop = asyncio.get_running_loop()
                with ThreadPoolExecutor() as pool:
                    if timeout:
                        result = await asyncio.wait_for(
                            loop.run_in_executor(pool, tool.run, input_data),
                            timeout=timeout,
                        )
                    else:
                        result = await loop.run_in_executor(pool, tool.run, input_data)
            elapsed = time.perf_counter() - start
            logger.info(f"[tool] '{tool.name}' completed in {elapsed:.2f}s")
            logger.debug(f"[tool] Result preview: {str(result)[:400]}")
            return result
        except Exception as e:
            logger.exception(f"[route_execution] Error: {e}")
            logger.warning(f"[tool] '{tool.name}' failed on attempt {attempt}: {e}")
            if attempt > retries:
                logger.error(
                    f"[tool] '{tool.name}' failed after {retries + 1} attempts."
                )
                raise
