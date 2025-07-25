# aegis/web/routes_backends.py
"""
API routes for listing available backend configurations.
"""
from pathlib import Path
from typing import List, Dict, Any

import yaml
from fastapi import APIRouter, HTTPException

from aegis.utils.logger import setup_logger

router = APIRouter()
logger = setup_logger(__name__)


@router.get("/backends", tags=["Configuration"])
def list_backends() -> List[Dict[str, Any]]:
    """
    Scans and returns a list of available backend profiles from backends.yaml.
    """
    logger.info("Request received to list backend profiles.")
    manifest_path = Path("backends.yaml")

    if not manifest_path.is_file():
        logger.error("backends.yaml not found.")
        raise HTTPException(status_code=404, detail="backends.yaml not found.")

    try:
        with manifest_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        profiles = data.get("backends", [])
        # Extract only the necessary info for the UI
        profile_info = [
            {"profile_name": p.get("profile_name"), "type": p.get("type")}
            for p in profiles
            if "profile_name" in p
        ]

        logger.info(f"Found {len(profile_info)} backend profiles.")
        return profile_info

    except Exception as e:
        logger.exception("Failed to load or parse backends.yaml")
        raise HTTPException(status_code=500, detail=str(e))
