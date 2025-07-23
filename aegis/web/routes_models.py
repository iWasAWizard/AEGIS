# aegis/web/routes_models.py
"""
API routes for listing available models for agent configuration.
"""
from typing import List

from fastapi import APIRouter, HTTPException

from aegis.utils.logger import setup_logger
from aegis.utils.model_manifest_loader import get_parsed_model_manifest, ModelEntry

router = APIRouter()
logger = setup_logger(__name__)


@router.get("/models", tags=["Configuration"])
def list_models() -> List[ModelEntry]:
    """
    Returns a list of available abstract models from AEGIS's model list.
    """
    logger.info("Request received to list abstract models.")
    try:
        manifest = get_parsed_model_manifest()
        return manifest.models
    except Exception as e:
        logger.exception("Failed to load or parse model manifest.")
        raise HTTPException(status_code=500, detail=str(e))
