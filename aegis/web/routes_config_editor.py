# aegis/web/routes_config_editor.py
"""
API routes for listing, reading, and writing to safelisted config files.
"""
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from aegis.utils.logger import setup_logger
from aegis.utils.config import clear_config_cache
from aegis.utils.backend_loader import clear_backend_manifest_cache
from aegis.utils.model_manifest_loader import clear_model_manifest_cache
from aegis.utils.theme_loader import clear_theme_cache

router = APIRouter(prefix="/editor", tags=["Config Editor"])
logger = setup_logger(__name__)

# Safelist of editable files and directories to prevent arbitrary file access
ALLOWED_FILES = ["config.yaml", "backends.yaml", "machines.yaml", "models.yaml"]
ALLOWED_DIRS = ["presets", "themes"]


def get_safelisted_files() -> List[str]:
    """Get a list of all safelisted configuration files."""
    files = [f for f in ALLOWED_FILES if Path(f).is_file()]
    for d in ALLOWED_DIRS:
        dir_path = Path(d)
        if dir_path.is_dir():
            files.extend(str(p.as_posix()) for p in dir_path.glob("*.yaml"))
    return sorted(files)


def is_path_safelisted(path_str: str) -> bool:
    """Check if a given file path is in our safelist."""
    path = Path(path_str).as_posix()
    return path in get_safelisted_files()


@router.get("/files", response_model=List[str])
def list_editable_files():
    """Returns a list of all YAML configuration files that are safe to edit."""
    return get_safelisted_files()


class FileContent(BaseModel):
    path: str
    content: str


@router.get("/file")
def get_file_content(path: str):
    """Reads and returns the content of a single safelisted config file."""
    if not is_path_safelisted(path):
        raise HTTPException(status_code=403, detail="File path is not allowed.")

    file_path = Path(path)
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found.")

    return {"path": path, "content": file_path.read_text(encoding="utf-8")}


@router.post("/file")
def save_file_content(payload: FileContent):
    """Saves content to a specific safelisted config file and clears caches."""
    path = payload.path
    content = payload.content

    if not is_path_safelisted(path):
        raise HTTPException(status_code=403, detail="File path is not allowed.")

    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        logger.info(
            f"Configuration file saved: {path}. Clearing caches for hot-reload."
        )

        # Invalidate all relevant caches
        clear_config_cache()
        clear_backend_manifest_cache()
        clear_model_manifest_cache()

        # If a theme file was edited, clear its specific cache
        if p.parent.name == "themes":
            clear_theme_cache()

        return {"status": "success", "path": path}
    except Exception as e:
        logger.exception(f"Failed to write to file: {path}")
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")
