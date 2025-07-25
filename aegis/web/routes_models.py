# aegis/web/routes_models.py
"""
API routes for listing available models for agent configuration.
"""
from typing import List

import httpx
from fastapi import APIRouter, HTTPException, Query

from aegis.utils.backend_loader import get_backend_config
from aegis.utils.logger import setup_logger
from aegis.utils.model_manifest_loader import get_parsed_model_manifest, ModelEntry

router = APIRouter()
logger = setup_logger(__name__)


@router.get("/models", tags=["Configuration"])
async def get_available_models(backend_profile: str = Query(...)) -> List[ModelEntry]:
    """
    Dynamically gets the list of available models from a specified backend.

    It queries the specified backend for its list of served models, then filters
    the full AEGIS model manifest to only show models that are both actively
    being served and are defined in models.yaml.
    """
    logger.info(f"Request to dynamically list models from backend: '{backend_profile}'")
    try:
        backend_config = get_backend_config(backend_profile)
        aegis_manifest = get_parsed_model_manifest()
        served_model_ids = []

        if backend_config.type in ("vllm", "openai"):
            base_url = backend_config.llm_url.rsplit("/", 2)[0]
            models_url = f"{base_url}/models"
            async with httpx.AsyncClient() as client:
                response = await client.get(models_url, timeout=10)
                response.raise_for_status()
                models_data = response.json()
                served_model_ids = [m["id"] for m in models_data.get("data", [])]

        elif backend_config.type == "koboldcpp" and backend_config.model:
            served_model_ids = [backend_config.model]

        if not served_model_ids:
            logger.warning(
                f"Backend '{backend_profile}' did not return any served models."
            )
            return []

        # Filter the main manifest to only include models that are actively served
        available_models = [
            model for model in aegis_manifest.models if model.name in served_model_ids
        ]
        logger.info(
            f"Found {len(available_models)} available models served by backend '{backend_profile}'."
        )
        return available_models

    except httpx.RequestError as e:
        logger.error(f"Failed to connect to backend service to list models: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Could not connect to the backend service at {getattr(backend_config, 'llm_url', 'unknown URL')}.",
        )
    except Exception as e:
        logger.exception(
            "An unexpected error occurred while fetching models from backend."
        )
        raise HTTPException(status_code=500, detail=str(e))
