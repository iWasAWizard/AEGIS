"""Initializes the web API module and makes FastAPI route modules importable."""

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


def mount_ui(app):
    """
    mount_ui.
    :param app: Description of app
    :type app: Any
    :return: Description of return value
    :rtype: Any
    """
    app.mount("/", StaticFiles(directory="aegis/web/ui", html=True), name="ui")


connected_clients = []


@router.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    """
    websocket_logs.
    :param websocket: Description of websocket
    :type websocket: Any
    :return: Description of return value
    :rtype: Any
    """
    logger.info("→ [__init__] Entering def()")
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
    broadcast_log.
    :param message: Description of message
    :type message: Any
    :return: Description of return value
    :rtype: Any
    """
    for ws in connected_clients:
        try:
            await ws.send_text(message)
        except Exception as e:
            logger.exception(f"[__init__] Error: {e}")
            logger.warning(f"[broadcast] Skipped a disconnected websocket: {e}")
