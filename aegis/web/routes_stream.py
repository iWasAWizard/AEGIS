# aegis/web/routes_stream.py
"""
Manages WebSocket connections and provides a logging handler to stream
logs to connected UI clients.
"""
import asyncio
import logging
from typing import List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter()

connected_clients: List[WebSocket] = []


async def broadcast_log(message: str):
    """Broadcasts a log message to all connected WebSocket clients."""
    if not connected_clients:
        return

    logger.debug(f"Broadcasting log message to {len(connected_clients)} clients.")
    tasks = [client.send_text(message) for client in connected_clients]
    await asyncio.gather(*tasks, return_exceptions=True)


@router.websocket("/logs")
async def websocket_logs_endpoint(websocket: WebSocket):
    """The FastAPI endpoint that clients connect to for receiving logs."""
    await websocket.accept()
    connected_clients.append(websocket)
    logger.info(
        f"New WebSocket client connected to log stream. Total clients: {len(connected_clients)}"
    )
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected.")
    except Exception as e:
        logger.error(f"An unexpected error occurred in the WebSocket connection: {e}")
    finally:
        if websocket in connected_clients:
            connected_clients.remove(websocket)
        logger.info(
            f"WebSocket client removed. Total clients: {len(connected_clients)}"
        )


class WebSocketLogHandler(logging.Handler):
    """A custom logging handler that broadcasts log records to WebSocket clients."""

    def __init__(self):
        """Initializes the handler and sets a color formatter."""
        super().__init__()
        from aegis.utils.logger import ColorFormatter

        self.setFormatter(ColorFormatter())

    def emit(self, record: logging.LogRecord):
        """Formats the log record and broadcasts it via the WebSocket."""
        if "routes_stream" in record.name:
            return

        try:
            msg = self.format(record)
            # This is a thread-safe way to call an async function from a synchronous one (like this handler).
            loop = asyncio.get_running_loop()
            asyncio.run_coroutine_threadsafe(broadcast_log(msg), loop)
        except RuntimeError:
            # This can happen if no event loop is running on the current thread. Safe to ignore.
            pass
        except Exception:
            self.handleError(record)
