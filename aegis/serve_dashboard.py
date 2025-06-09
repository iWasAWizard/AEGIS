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
from aegis.web.log_streamer import WebSocketLogHandler

# Load environment variables from a .env file if it exists.
load_dotenv()

# Setup the logger first. This configures console and file logging.
logger = setup_logger(__name__)

# Initialize the FastAPI application.
app = FastAPI(
    title="AEGIS Agentic Framework",
    description="An autonomous agent framework for planning and executing complex tasks.",
    version="1.0.0",
)

# --- Tool and Route Registration ---


@app.on_event("startup")
def on_startup():
    """Actions to perform on application startup."""
    # 1. Log critical configuration details from the environment
    logger.info("--- AEGIS Configuration ---")
    logger.info(f"OLLAMA_MODEL: {os.getenv('OLLAMA_MODEL', 'Not Set')}")
    logger.info(
        f"OLLAMA_API_URL: {os.getenv('OLLAMA_API_URL', 'http://ollama:11434/api/generate')}"
    )
    logger.info("--------------------------")

    # 2. Import all tools to populate the TOOL_REGISTRY.
    logger.info("Importing all available tools...")
    import_all_tools()
    log_registry_contents()

    # 3. Add the WebSocket handler to the root logger.
    # This connects our web UI to the centralized logging system.
    root_logger = logging.getLogger()
    root_logger.addHandler(WebSocketLogHandler())
    logger.info("WebSocket log handler configured and attached to root logger.")


# Include all API routes from the web module.
app.include_router(api_router, prefix="/api")
logger.info("All API routes registered under the /api prefix.")

# Mount the static React UI files.
# This serves the built React application from the root URL.
ui_path = "aegis/web/react_ui/dist"
if os.path.exists(ui_path):
    app.mount("/", StaticFiles(directory=ui_path, html=True), name="ui")
    logger.info(f"React UI mounted from directory: {ui_path}")
else:
    logger.warning(f"UI directory not found at '{ui_path}'. The UI will not be served.")

# --- Main Server Execution ---

if __name__ == "__main__":
    logger.info("Preparing to launch AEGIS web server...")

    # Load server configuration from environment variables with sensible defaults.
    host = os.getenv("AEGIS_HOST", "0.0.0.0")
    port = int(os.getenv("AEGIS_PORT", 8000))
    log_level = os.getenv("AEGIS_LOG_LEVEL", "info").lower()
    reload = os.getenv("AEGIS_RELOAD", "false").lower() == "true"

    logger.info(f"Server will run on http://{host}:{port}")
    logger.info(f"Log level set to: {log_level}")
    logger.info(f"Hot-reloading enabled: {reload}")

    # Start the Uvicorn server.
    uvicorn.run(
        "aegis.serve_dashboard:app",
        host=host,
        port=port,
        log_level=log_level,
        reload=reload,
    )
