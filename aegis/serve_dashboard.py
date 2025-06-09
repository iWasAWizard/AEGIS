# aegis/serve_dashboard.py
"""
Launches the FastAPI web server for the AEGIS dashboard and API.

This script initializes the FastAPI application, registers all API routes from
the `aegis.web` module, loads all available tools into the registry, and starts
the Uvicorn server. It is the main entry point for running AEGIS in web mode.
"""
import logging
import os

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from aegis.registry import log_registry_contents
from aegis.utils.logger import setup_logger
from aegis.utils.tool_loader import import_all_tools
from aegis.web import router as api_router
from aegis.web.routes_stream import WebSocketLogHandler

load_dotenv()
logger = setup_logger(__name__)

app = FastAPI(
    title="AEGIS Agentic Framework",
    description="An autonomous agent framework for planning and executing complex tasks.",
    version="1.0.0",
)


@app.on_event("startup")
def on_startup():
    """Performs application startup actions.

    This function is executed by FastAPI when the server starts. It handles
    logging critical configurations, dynamically importing all available tools
    into the registry, and attaching the WebSocket handler to the root logger
    to enable live log streaming to the UI.
    """
    logger.info("--- AEGIS Application Startup ---")
    logger.info(f"OLLAMA_MODEL: {os.getenv('OLLAMA_MODEL', 'Not Set')}")
    logger.info(f"OLLAMA_API_URL: {os.getenv('OLLAMA_API_URL', 'http://ollama:11434/api/generate')}")

    logger.info("Importing all available tools...")
    import_all_tools()
    log_registry_contents()

    # Attach the WebSocket handler to the root logger so it captures all logs
    root_logger = logging.getLogger()
    if not any(isinstance(h, WebSocketLogHandler) for h in root_logger.handlers):
        root_logger.addHandler(WebSocketLogHandler())
        logger.info("WebSocket log handler configured and attached to root logger.")
    else:
        logger.info("WebSocket log handler already attached.")


# Include all API routes defined in the aegis.web package
app.include_router(api_router, prefix="/api")
logger.info("All API routes registered under the /api prefix.")

# Serve the static React UI files
ui_path = "aegis/web/react_ui/dist"
if os.path.exists(ui_path):
    app.mount("/", StaticFiles(directory=ui_path, html=True), name="ui")
    logger.info(f"React UI mounted from directory: {ui_path}")
else:
    logger.warning(f"UI directory not found at '{ui_path}'. The UI will not be served.")

if __name__ == "__main__":
    """Main entry point for running the server directly."""
    logger.info("Preparing to launch AEGIS web server...")

    host = os.getenv("AEGIS_HOST", "0.0.0.0")
    port = int(os.getenv("AEGIS_PORT", 8000))
    log_level = os.getenv("AEGIS_LOG_LEVEL", "info").lower()
    reload = os.getenv("AEGIS_RELOAD", "false").lower() == "true"

    logger.info(f"Server will run on http://{host}:{port}")
    logger.info(f"Uvicorn log level set to: {log_level}")
    logger.info(f"Hot-reloading enabled: {reload}")

    uvicorn.run("aegis.serve_dashboard:app", host=host, port=port, log_level=log_level, reload=reload)
