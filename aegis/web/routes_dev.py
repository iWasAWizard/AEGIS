# aegis/web/routes_dev.py
"""
API routes for developer-focused actions like validation and scaffolding.
"""
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from aegis.utils.cli_helpers import validate_all_configs, create_new_tool
from aegis.utils.logger import setup_logger

router = APIRouter(prefix="/dev", tags=["Developer"])
logger = setup_logger(__name__)


class NewToolRequest(BaseModel):
    name: str
    description: str
    category: str
    is_safe: bool


@router.post("/validate-configs")
def validate_configs_endpoint():
    """Validates all key configuration files and returns the results."""
    try:
        results = validate_all_configs()
        return {"status": "ok", "results": results}
    except Exception as e:
        logger.exception("Configuration validation via API failed.")
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {e}"
        )


@router.post("/new-tool")
def new_tool_endpoint(payload: NewToolRequest):
    """Creates a new boilerplate tool file in the 'plugins/' directory."""
    try:
        file_path = create_new_tool(
            name=payload.name,
            description=payload.description,
            category=payload.category,
            is_safe=payload.is_safe,
        )
        return {"status": "ok", "file_path": str(file_path)}
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.exception("New tool creation via API failed.")
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {e}"
        )
