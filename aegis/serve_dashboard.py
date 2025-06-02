"""
Launches the FastAPI server and registers all API routes for the agentic dashboard.
"""

import os

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI

from aegis.utils.logger import setup_logger
from aegis.web.routes.model_info import router as model_info_router
from aegis.web.routes_artifacts import router as artifacts_router
from aegis.web.routes_compare import router as compare_router
from aegis.web.routes_debug import router as debug_router
from aegis.web.routes_launch import router as launch_router
from aegis.web.routes_presets import router as presets_router
from aegis.web.routes_tasks import router as inventory_router

logger = setup_logger(__name__)
load_dotenv()

app = FastAPI()

# Register all routers
app.include_router(artifacts_router)
app.include_router(compare_router)
app.include_router(inventory_router)
app.include_router(launch_router)
app.include_router(presets_router)
app.include_router(debug_router)
app.include_router(model_info_router)

logger.info("All API routes registered successfully.")

if __name__ == "__main__":
    logger.info("Starting dashboard server")
    port = int(os.getenv("DASHBOARD_PORT", 8000))
    host = os.getenv("DASHBOARD_HOST", "0.0.0.0")
    debug = os.getenv("DASHBOARD_DEBUG", "false").lower() == "true"
    logger.info(f"Running on {host}:{port} (debug={debug})")
    app.include_router(model_info_router.router)
    app.include_router(launch_router.router)
    app.include_router(debug_router.router)
    uvicorn.run(app, host=host, port=port)
