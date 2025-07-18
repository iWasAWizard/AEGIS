# aegis/utils/theme_loader.py
"""
Utility for loading and caching UI theme configurations.
"""
import functools
from pathlib import Path
from typing import Optional

import yaml
from pydantic import ValidationError

from aegis.schemas.theme import ThemeConfig
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)

THEMES_DIR = Path("themes")

# A hardcoded fallback theme to ensure the UI is always usable.
OLED_FALLBACK = ThemeConfig(
    name="OLED (Fallback)",
    description="Default fallback theme.",
    properties={
        "bg": "#000000",
        "fg": "#ffffff",
        "border": "#444444",
        "accent": "#3b82f6",
        "input-bg": "#111111",
        "input-fg": "#ffffff",
        "font": "'Segoe UI', sans-serif",
        "font-size": "16px",
    },
)


@functools.cache
def get_theme_config(theme_name: str) -> ThemeConfig:
    """
    Loads, validates, and caches a single theme config from a YAML file.
    Falls back to a default theme if the requested theme is invalid or not found.
    """
    logger.info(f"Loading theme config for: {theme_name}")
    theme_file = THEMES_DIR / f"{theme_name}.yaml"

    if not theme_file.is_file():
        logger.warning(f"Theme file not found: '{theme_file}'. Using fallback.")
        return OLED_FALLBACK

    try:
        with theme_file.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return ThemeConfig(**data)
    except (yaml.YAMLError, ValidationError) as e:
        logger.error(
            f"Failed to load or validate theme '{theme_name}': {e}. Using fallback."
        )
        return OLED_FALLBACK


def list_theme_files() -> list[str]:
    """Returns a list of available theme file stems from the themes directory."""
    if not THEMES_DIR.is_dir():
        return []
    return sorted([p.stem for p in THEMES_DIR.glob("*.yaml")])


def clear_theme_cache(theme_name: Optional[str] = None):
    """Clears the cache for a specific theme or all themes."""
    if theme_name:
        get_theme_config.cache_clear()  # Simplest way is to clear the whole cache
        logger.info(f"Cleared cache for theme: {theme_name}")
    else:
        get_theme_config.cache_clear()
        logger.info("Cleared all theme caches.")
