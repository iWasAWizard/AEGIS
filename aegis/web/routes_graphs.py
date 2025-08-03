# aegis/web/routes_graphs.py
"""Routes for visualizing or exporting execution graphs, timelines, or state transitions."""
import os
from pathlib import Path

import yaml
from fastapi import APIRouter, HTTPException, UploadFile, File

from aegis.utils.config import get_config
from aegis.utils.logger import setup_logger

config = get_config()
# This assumes that 'presets' is a subdirectory relative to where the app runs.
# A more robust solution might use an absolute path or resolve relative to the project root.
PRESET_DIR = Path(config.get("paths", {}).get("presets", "presets"))
router = APIRouter(prefix="/graphs", tags=["graphs"])
logger = setup_logger(__name__)


@router.get("/", summary="List saved AgentGraphConfig files")
def list_graphs():
    """Return a list of available graph configuration files from the presets directory.

    :return: List of graph filenames.
    :rtype: list[str]
    """
    logger.info("Listing available graph configuration files.")
    if not PRESET_DIR.exists():
        return []
    return sorted(
        f.name for f in PRESET_DIR.iterdir() if f.name.endswith((".yaml", ".yml"))
    )


@router.post("/upload", summary="Upload an AgentGraphConfig YAML file")
def upload_graph(file: UploadFile = File(...)):
    """Accept a YAML upload and save it to the presets directory.

    :param file: The file to upload.
    :type file: UploadFile
    :return: A dictionary with the result status and filename.
    :rtype: dict
    :raises HTTPException: If the file is invalid or cannot be saved.
    """
    logger.info(f"Attempting to upload graph file: {file.filename}")
    PRESET_DIR.mkdir(parents=True, exist_ok=True)

    file_path = PRESET_DIR / file.filename
    try:
        content = file.file.read()
        # Basic validation to ensure it's valid YAML
        yaml.safe_load(content)
        with open(file_path, "wb") as f:
            f.write(content)
        logger.info(f"Graph file saved successfully to: {file_path}")
    except Exception as e:
        logger.exception(f"Error saving uploaded graph file '{file.filename}': {e}")
        raise HTTPException(status_code=400, detail=f"Invalid file or save error: {e}")

    return {"status": "ok", "filename": file.filename}


@router.get("/view", summary="Retrieve contents of a saved AgentGraphConfig")
def view_graph(name: str):
    """Load a saved graph file from presets and return its JSON-compatible content.

    :param name: Filename of the graph to retrieve (e.g., 'default.yaml').
    :type name: str
    :return: The parsed dictionary content of the graph config.
    :rtype: dict
    :raises HTTPException: If the file cannot be found or loaded.
    """
    logger.info(f"Request to view graph: {name}")
    path = PRESET_DIR / name
    if not path.exists():
        logger.warning(f"Graph file not found at path: {path}")
        raise HTTPException(status_code=404, detail="Graph not found")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.exception(f"Failed to read or parse graph file '{name}': {e}")
        raise HTTPException(status_code=500, detail=f"Error reading graph file: {e}")
