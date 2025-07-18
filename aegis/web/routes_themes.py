# aegis/web/routes_themes.py
"""
API routes for fetching UI theme data.
"""
from typing import List

from fastapi import APIRouter, HTTPException

from aegis.schemas.theme import ThemeConfig
from aegis.utils.theme_loader import get_theme_config, list_theme_files
from aegis.utils.logger import setup_logger

router = APIRouter(prefix="/themes", tags=["UI Configuration"])
logger = setup_logger(__name__)


@router.get("", response_model=List[str])  # Corrected path from "/" to ""
def get_theme_list():
    """Returns a list of available theme names."""
    return list_theme_files()


@router.get("/{theme_name}", response_model=ThemeConfig)
def get_theme_details(theme_name: str):
    """Returns the properties for a specific theme."""
    try:
        theme_data = get_theme_config(theme_name)
        return theme_data
    except Exception as e:
        logger.exception(f"Error fetching details for theme '{theme_name}'.")
        raise HTTPException(status_code=500, detail=str(e))
