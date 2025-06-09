# aegis/web/__init__.py
"""Initializes the web API module and makes FastAPI route modules importable."""

from fastapi import APIRouter
from fastapi.staticfiles import StaticFiles

from aegis.utils.logger import setup_logger
from aegis.web.log_streamer import router as log_streamer_router
from aegis.web.routes_artifacts import router as artifacts_router
from aegis.web.routes_compare import router as compare_router
from aegis.web.routes_debug import router as debug_router
from aegis.web.routes_fuzz import router as fuzz_router
from aegis.web.routes_graphs import router as graphs_router
from aegis.web.routes_inventory import router as inventory_router
from aegis.web.routes_launch import router as launch_router
from aegis.web.routes_presets import router as presets_router
from aegis.web.routes_reports import router as reports_router
from aegis.web.routes_tasks import router as tasks_router
from aegis.web.routes_logs import router as logs_router

logger = setup_logger(__name__)

# This is the main router for the /api prefix.
router = APIRouter()

# Include all the individual route files.
router.include_router(presets_router)
router.include_router(compare_router)
router.include_router(artifacts_router)
router.include_router(inventory_router)
router.include_router(launch_router)
router.include_router(tasks_router)
router.include_router(fuzz_router)
router.include_router(debug_router)
router.include_router(logs_router)  # This is for /status, /echo etc
router.include_router(graphs_router)
router.include_router(reports_router)

# Include the WebSocket log streamer router
router.include_router(log_streamer_router)


# This function is no longer needed here, but keeping it in case you
# want to mount the UI from a different location in the future.
async def mount_ui(app):
    """
    mount_ui.
    :param app: Description of app
    :type app: Any
    :return: Description of return value
    :rtype: Any
    """
    app.mount("/", StaticFiles(directory="aegis/web/ui", html=True), name="ui")
