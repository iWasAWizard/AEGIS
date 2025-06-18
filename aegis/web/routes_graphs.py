# aegis/web/routes_graphs.py
"""Routes for visualizing or exporting execution graphs, timelines, or state transitions."""

import os

import yaml
from fastapi import APIRouter, HTTPException, UploadFile, File

from aegis.utils.logger import setup_logger

GRAPH_DIR = "presets"
router = APIRouter(prefix="/graphs", tags=["graphs"])
logger = setup_logger(__name__)


@router.get("/", summary="List saved AgentGraphConfig files")
def list_graphs():
    """Return a list of available graph configuration files from the presets directory.

    :return: List of graph filenames.
    :rtype: list[str]
    """
    logger.info("Listing available graph configuration files.")
    if not os.path.exists(GRAPH_DIR):
        return []
    return sorted(f for f in os.listdir(GRAPH_DIR) if f.endswith((".yaml", ".yml")))


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
    if not os.path.exists(GRAPH_DIR):
        os.makedirs(GRAPH_DIR)

    file_path = os.path.join(GRAPH_DIR, file.filename)  # type: ignore
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
    path = os.path.join(GRAPH_DIR, name)
    if not os.path.exists(path):
        logger.warning(f"Graph file not found at path: {path}")
        raise HTTPException(status_code=404, detail="Graph not found")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.exception(f"Failed to read or parse graph file '{name}': {e}")
        raise HTTPException(status_code=500, detail=f"Error reading graph file: {e}")
