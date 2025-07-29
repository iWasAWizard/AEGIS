# aegis/web/routes_backend_info.py
"""
API routes for dynamically querying backend services for their configuration.
"""
from typing import List

import httpx
from fastapi import APIRouter, HTTPException

from aegis.utils.backend_loader import get_backend_config
from aegis.utils.config import get_config
from aegis.utils.logger import setup_logger
from aegis.utils.model_manifest_loader import get_parsed_model_manifest, ModelEntry

router = APIRouter()
logger = setup_logger(__name__)


@router.get("/backend/models", tags=["Backend Info"])
async def get_available_models() -> List[ModelEntry]:
    """
    Dynamically gets the list of available models from the default backend.

    It queries the specified backend for its list of served models, then filters
    the full AEGIS model manifest to only show models that are both actively
    being served and are defined in models.yaml.
    """
    logger.info("Request received to dynamically list models from the default backend.")
    try:
        system_config = get_config()
        default_profile_name = system_config.get("defaults", {}).get("backend_profile")
        if not default_profile_name:
            raise HTTPException(
                status_code=500,
                detail="No default backend_profile defined in config.yaml.",
            )

        backend_config = get_backend_config(default_profile_name)
        aegis_manifest = get_parsed_model_manifest()
        available_models = []

        if backend_config.type in ("vllm", "openai"):
            base_url = backend_config.llm_url.rsplit("/", 2)[0]
            models_url = f"{base_url}/models"
            async with httpx.AsyncClient() as client:
                response = await client.get(models_url, timeout=10)
                response.raise_for_status()
                models_data = response.json()
                served_model_ids = [m["id"] for m in models_data.get("data", [])]
            available_models = [
                model
                for model in aegis_manifest.models
                if model.name in served_model_ids
            ]
        elif backend_config.type == "ollama":
            tags_url = f"{backend_config.llm_url}/api/tags"
            async with httpx.AsyncClient() as client:
                response = await client.get(tags_url, timeout=10)
                response.raise_for_status()
                models_data = response.json()
                served_model_ids = [m["name"] for m in models_data.get("models", [])]
            available_models = [
                model
                for model in aegis_manifest.models
                if model.ollama_model_name in served_model_ids
            ]

        if not available_models:
            logger.warning(
                f"Backend '{default_profile_name}' did not return any served models that are also in models.yaml."
            )
            return []

        logger.info(
            f"Found {len(available_models)} available models served by backend '{default_profile_name}'."
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
