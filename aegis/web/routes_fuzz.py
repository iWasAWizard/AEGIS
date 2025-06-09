# aegis/web/routes_fuzz.py
"""Fuzz testing routes that expose tools and interfaces to randomized or invalid input patterns."""

from typing import Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ValidationError

from aegis.exceptions import ToolExecutionError
from aegis.registry import TOOL_REGISTRY
from aegis.utils.logger import setup_logger

router = APIRouter(prefix="/fuzz", tags=["fuzzing"])
logger = setup_logger(__name__)


class FuzzToolRequest(BaseModel):
    """Represents a request to run a registered fuzzing tool.

    :ivar tool_name: The name of the registered tool to fuzz.
    :vartype tool_name: str
    :ivar payload: A dictionary of input parameters for the tool.
    :vartype payload: Dict[str, Any]
    """

    tool_name: str
    payload: Dict[str, Any]


@router.get("/", summary="List available fuzz tools")
def list_fuzz_tools() -> list[str]:
    """Lists all registered tools tagged with 'fuzz'.

    This endpoint allows the UI or other clients to discover which fuzzing
    capabilities are currently available in the agent.

    :return: A list of fuzz tool names.
    :rtype: list[str]
    """
    logger.info("Fuzzing tools list requested.")
    return [name for name, entry in TOOL_REGISTRY.items() if "fuzz" in entry.tags]


@router.post("/run", summary="Run a registered fuzz tool")
def run_fuzz_tool(req: FuzzToolRequest) -> dict:
    """Executes a registered fuzz tool using a provided input payload.

    :param req: The request containing the tool name and payload.
    :type req: FuzzToolRequest
    :return: The output of the fuzzing tool.
    :rtype: dict
    :raises HTTPException: If the tool is not found, input is invalid, or execution fails.
    """
    logger.info(f"Received request to run fuzz tool: '{req.tool_name}'")
    entry = TOOL_REGISTRY.get(req.tool_name)

    if not entry:
        logger.warning(f"Fuzz tool not found: '{req.tool_name}'")
        raise HTTPException(status_code=404, detail="Tool not found")
    if "fuzz" not in entry.tags:
        logger.warning(f"Requested tool '{req.tool_name}' is not a fuzz tool.")
        raise HTTPException(status_code=403, detail="Tool is not a fuzz tool")

    try:
        model = entry.input_model(**req.payload)
        logger.debug(f"Running fuzz tool '{req.tool_name}' with payload: {req.payload}")
        result = entry.run(model)
        logger.info(f"Fuzz tool '{req.tool_name}' executed successfully.")
        return {"result": result}
    except ValidationError as e:
        logger.error(f"Validation error for fuzz tool '{req.tool_name}': {e}")
        raise HTTPException(status_code=400, detail=f"Invalid payload: {e}")
    except ToolExecutionError as e:
        logger.exception(f"Execution error in fuzz tool '{req.tool_name}'")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception(f"Unexpected error during fuzz tool execution: '{req.tool_name}'")
        raise HTTPException(status_code=500, detail=f"An unexpected internal error occurred: {e}")
