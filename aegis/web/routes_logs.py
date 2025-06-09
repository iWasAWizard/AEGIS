# aegis/web/routes_logs.py
"""Debug routes for internal agent inspection, configuration review, or runtime introspection."""

import datetime
import os
import platform
from typing import Dict, Any

from dotenv import load_dotenv
from fastapi import APIRouter

from aegis.utils.logger import setup_logger

load_dotenv()
router = APIRouter()
logger = setup_logger(__name__)
os.getenv("LOG_LEVEL", "debug")


@router.post("/echo", summary="Echo back posted data")
def echo_post(payload: Dict[str, Any]):
    """A simple debug endpoint that returns the exact payload it was sent.

    Useful for testing client requests and connectivity.

    :param payload: Arbitrary dictionary data.
    :type payload: dict
    :return: Dictionary containing the echoed payload.
    :rtype: dict
    """
    logger.debug(f"Echo POST payload: {payload}")
    return {"echo": payload}


@router.get("/status", summary="Basic runtime system status")
def system_status():
    """Provides current system diagnostics and environment status.

    This endpoint returns basic information about the running server process,
    including server time, platform details, and key environment variables.

    :return: Dictionary containing system status information.
    :rtype: dict
    """
    logger.info("System status requested")
    return {
        "server_time": datetime.datetime.now().isoformat(),
        "platform": platform.system(),
        "node": platform.node(),
        "python_version": platform.python_version(),
        "cwd": os.getcwd(),
        "safe_mode": os.getenv("SAFE_MODE", "true"),
    }
