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

    For OpenAI-compatible backends (like vLLM), it queries the /v1/models endpoint.
    It then filters the full AEGIS model manifest to only show models that are
    actively being served by the backend.
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
        served_model_names = []

        if backend_config.type in ("vllm", "openai"):
            # OpenAPI-compatible endpoints have a /models endpoint
            base_url = backend_config.llm_url.rsplit("/", 2)[0]
            models_url = f"{base_url}/models"
            async with httpx.AsyncClient() as client:
                response = await client.get(models_url, timeout=10)
                response.raise_for_status()
                models_data = response.json()
                served_model_names = [m["id"] for m in models_data.get("data", [])]
        elif backend_config.type == "koboldcpp":
            # Kobold serves one model at a time, defined in its config
            served_model_names = [backend_config.model]

        if not served_model_names:
            logger.warning("Backend did not return any served models.")
            return []

        # Filter the main manifest to only include models that are actively served
        available_models = [
            model for model in aegis_manifest.models if model.name in served_model_names
        ]
        logger.info(
            f"Found {len(available_models)} available models served by backend '{default_profile_name}'."
        )
        return available_models

    except httpx.RequestError as e:
        logger.error(f"Failed to connect to backend service to list models: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Could not connect to the backend service at {backend_config.llm_url}.",
        )
    except Exception as e:
        logger.exception(
            "An unexpected error occurred while fetching models from backend."
        )
        raise HTTPException(status_code=500, detail=str(e))
