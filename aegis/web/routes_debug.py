"""Fuzz testing routes that expose tools and interfaces to randomized or invalid input patterns."""

from typing import Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from aegis.registry import TOOL_REGISTRY
from aegis.utils.logger import setup_logger

router = APIRouter(prefix="/fuzz", tags=["fuzzing"])
logger = setup_logger(__name__)


class FuzzToolRequest(BaseModel):
    """
    Represents a request to run a registered fuzzing tool.

    :param tool_name: The name of the registered tool to fuzz
    :param payload: A dictionary of input parameters for the tool
    """
    tool_name: str
    payload: Dict[str, Any]


@router.get("/", summary="List available fuzz tools")
def list_fuzz_tools():
    """
    List all registered tools tagged with 'fuzz'.

    :return: List of fuzz tool names
    :rtype: List[str]
    """
    logger.info("Listing fuzz tools")
    return [name for name, entry in TOOL_REGISTRY.items() if "fuzz" in entry.tags]


@router.post("/run", summary="Run a registered fuzz tool")
def run_fuzz_tool(req: FuzzToolRequest):
    """
    Execute a registered fuzz tool using provided input payload.

    :param req: Tool name and payload to run
    :type req: FuzzToolRequest
    :return: Tool output or error message
    :rtype: dict
    :raises HTTPException: if tool not found, not tagged as fuzz, or fails
    """
    logger.debug(f"Running fuzz tool: {req.tool_name} with payload: {req.payload}")
    entry = TOOL_REGISTRY.get(req.tool_name)
    if not entry:
        logger.warning(f"Fuzz tool not found: {req.tool_name}")
        raise HTTPException(status_code=404, detail="Tool not found")
    if "fuzz" not in entry.tags:
        logger.warning(f"Requested tool is not tagged as fuzz: {req.tool_name}")
        raise HTTPException(status_code=403, detail="Tool is not a fuzz tool")
    try:
        model = entry.input_model(**req.payload)
        result = entry.func(model)
        return {"result": result}
    except Exception:
        logger.exception(f"Error during fuzz tool execution: {req.tool_name}")
        raise HTTPException(status_code=500, detail="Internal tool error")
