"""Routes for visualizing or exporting execution graphs, timelines, or state transitions."""

import json
import os

from fastapi import APIRouter, HTTPException, UploadFile, File

from aegis.utils.logger import setup_logger

GRAPH_DIR = "graphs"
router = APIRouter(prefix="/graphs", tags=["graphs"])
logger = setup_logger(__name__)


@router.get("/", summary="List saved AgentGraphConfig files")
def list_graphs():
    """
    Return a list of available graph configuration files.

    :return: List of graph filenames
    :rtype: list[str]
    """
    logger.info("Listing graph configs")
    if not os.path.exists(GRAPH_DIR):
        return []
    return sorted(f for f in os.listdir(GRAPH_DIR) if f.endswith(".json"))


@router.post("/upload", summary="Upload an AgentGraphConfig JSON file")
def upload_graph(file: UploadFile = File(...)):
    """
    Accept a JSON upload and save it to the graphs directory.

    :param file: File to upload
    :type file: UploadFile
    :return: Result status
    :rtype: dict
    :raises HTTPException: if the file is invalid
    """
    logger.info(f"Uploading graph: {file.filename}")
    if not os.path.exists(GRAPH_DIR):
        os.makedirs(GRAPH_DIR)

    file_path = os.path.join(GRAPH_DIR, file.filename)
    try:
        content = file.file.read()
        json.loads(content)  # validate JSON
        with open(file_path, "wb") as f:
            f.write(content)
        logger.info(f"Graph saved: {file_path}")
    except Exception as e:
        logger.exception(f"[routes_graphs] Error: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid file: {e}")

    return {"status": "ok", "filename": file.filename}


@router.get("/view", summary="Retrieve contents of a saved AgentGraphConfig")
def view_graph(name: str):
    """
    Load a saved graph file from disk and return its JSON content.

    :param name: Filename to retrieve
    :type name: str
    :return: Parsed graph config
    :rtype: dict
    :raises HTTPException: if the file cannot be loaded
    """
    logger.info(f"Viewing graph: {name}")
    path = os.path.join(GRAPH_DIR, name)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Graph not found")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.exception(f"[ERROR] Failed to read graph: {name}")
        raise HTTPException(status_code=500, detail=f"{e}")
