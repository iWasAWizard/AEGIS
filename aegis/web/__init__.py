# aegis/web/__init__.py
"""
Initializes the web API module and makes FastAPI route modules importable.

This `__init__.py` file aggregates all the individual router objects from the
`routes_*` modules into a single `APIRouter` instance. This allows the main
FastAPI application in `serve_dashboard.py` to include all API endpoints
under a common prefix (e.g., `/api`) with a single line.
"""

from fastapi import APIRouter

from aegis.utils.logger import setup_logger
from aegis.web.routes_artifacts import router as artifacts_router
from aegis.web.routes_compare import router as compare_router
from aegis.web.routes_fuzz import router as fuzz_router
from aegis.web.routes_graphs import router as graphs_router
from aegis.web.routes_inventory import router as inventory_router
from aegis.web.routes_launch import router as launch_router
from aegis.web.routes_logs import router as logs_router
from aegis.web.routes_presets import router as presets_router
from aegis.web.routes_stream import router as log_streamer_router

logger = setup_logger(__name__)

# This is the main router for the /api prefix.
router = APIRouter()

# Include all the individual route files.
router.include_router(presets_router)
router.include_router(compare_router)
router.include_router(artifacts_router)
router.include_router(inventory_router)
router.include_router(launch_router)
router.include_router(fuzz_router)
router.include_router(logs_router)
router.include_router(graphs_router)
router.include_router(log_streamer_router, prefix="/ws")
