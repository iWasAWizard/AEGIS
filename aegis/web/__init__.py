"""
Web API initializer for AEGIS.

Sets up FastAPI routers, WebSocket endpoints, and static UI mounting.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

from aegis.utils.logger import setup_logger
from aegis.web.routes_artifacts import router as artifacts_router
from aegis.web.routes_compare import router as compare_router
from aegis.web.routes_debug import router as debug_router
from aegis.web.routes_fuzz import router as fuzz_router
from aegis.web.routes_graphs import router as graphs_router
from aegis.web.routes_inventory import router as inventory_router
from aegis.web.routes_launch import router as launch_router
from aegis.web.routes_logs import router as logs_router
from aegis.web.routes_presets import router as presets_router
from aegis.web.routes_reports import router as reports_router
from aegis.web.routes_tasks import router as tasks_router

logger = setup_logger(__name__)
router = APIRouter()

# Register all route modules
router.include_router(presets_router)
router.include_router(compare_router)
router.include_router(artifacts_router)
router.include_router(inventory_router)
router.include_router(launch_router)
router.include_router(tasks_router)
router.include_router(fuzz_router)
router.include_router(debug_router)
router.include_router(logs_router)
router.include_router(graphs_router)
router.include_router(reports_router)


# Serve frontend UI
def mount_ui(app):
    """
    Mounts the static UI frontend onto the FastAPI app.

    :param app: FastAPI app instance
    """
    app.mount("/", StaticFiles(directory="aegis/web/ui", html=True), name="ui")


# WebSocket for live log streaming
connected_clients = []


@router.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    """
    Accepts a WebSocket connection for real-time log streaming.

    :param websocket: Incoming WebSocket connection
    """
    logger.info("→ [__init__] Entering websocket_logs()")
    await websocket.accept()
    connected_clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected.")
        connected_clients.remove(websocket)


async def broadcast_log(message: str):
    """
    Broadcasts a log message to all connected WebSocket clients.

    :param message: Log message to send
    """
    for ws in connected_clients:
        try:
            await ws.send_text(message)
        except Exception as e:
            logger.exception(f"[__init__] Error: {e}")
            logger.warning(f"[broadcast_log] Skipped a disconnected websocket: {e}")
