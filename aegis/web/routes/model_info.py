"""Exposes FastAPI route to query the active LLM model used for generation."""

import subprocess

from fastapi import APIRouter

from aegis.utils.logger import setup_logger

router = APIRouter()
logger = setup_logger(__name__)


@router.get("/model/info")
def get_model_info():
    """
    Return the current Ollama model name.
    """
    try:
        result = subprocess.run(
            ["ollama", "list"], capture_output=True, text=True, check=True
        )
        models = result.stdout.strip().splitlines()
        for line in models[1:]:
            parts = line.split()
            if parts:
                return {"model": parts[0]}
        return {"model": None, "error": "No models found"}
    except Exception as e:
        logger.exception("Failed to fetch model info")
        return {"error": str(e)}
