# aegis/serve_dashboard.py
"""
Launches the FastAPI web server for the AEGIS dashboard and API.

This script initializes the FastAPI application, registers all API routes from
the `aegis.web` module, loads all available tools into the registry, and starts
the Uvicorn server. It is the main entry point for running AEGIS in web mode.
"""
import asyncio
import importlib
import logging
import os
import sys

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from aegis.exceptions import AegisError
from aegis.registry import log_registry_contents
from aegis.utils.logger import setup_logger
from aegis.utils.tool_loader import import_all_tools
from aegis.web import router as api_router
from aegis.web.routes_stream import WebSocketLogHandler, connected_clients

# OpenTelemetry Imports
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor


load_dotenv()
logger = setup_logger(__name__)

app = FastAPI(
    title="AEGIS Agentic Framework",
    description="An autonomous agent framework for planning and executing complex tasks.",
    version="1.0.0",
)


@app.exception_handler(AegisError)
async def aegis_exception_handler(request: Request, exc: AegisError):
    """Handles all custom application errors and returns a structured JSON response."""
    logger.error(f"Caught an AegisError: {exc.__class__.__name__}: {exc}")
    logger.error(f"Request details: {request}")
    return JSONResponse(
        status_code=500,
        content={"error_type": exc.__class__.__name__, "message": str(exc)},
    )


def validate_critical_imports():
    """
    Tries to import all critical modules at startup.
    If any import fails, logs a fatal error and exits. This prevents silent failures
    where a route is called and the server worker crashes due to a ModuleNotFoundError.
    """
    logger.info("Performing critical import validation...")
    critical_modules = [
        "aegis.agents.agent_graph",
        "aegis.agents.task_state",
        "aegis.schemas.agent",
        "aegis.schemas.plan_output",
        "aegis.agents.steps.execute_tool",
        "aegis.agents.steps.reflect_and_plan",
        "aegis.agents.steps.summarize_result",
        "aegis.agents.steps.check_termination",
        "aegis.agents.steps.verification",
    ]
    for module in critical_modules:
        try:
            importlib.import_module(module)
            logger.debug(f"✅ Successfully imported '{module}'")
        except (ImportError, ModuleNotFoundError) as e:
            logger.critical(f"❌ FATAL: A critical module failed to import: '{module}'")
            logger.critical(f"  Error: {e}")
            logger.critical(
                "  This is likely due to an incorrect relative import "
                "(e.g., 'from schemas...' instead of 'from aegis.schemas...')."
            )
            logger.critical(
                "  The application cannot start. Please fix the import and restart."
            )
            sys.exit(1)
    logger.info("✅ All critical imports validated successfully.")


@app.on_event("startup")
def on_startup():
    """Performs application startup actions."""
    logger.info("--- AEGIS Application Startup ---")

    # --- OpenTelemetry Tracing Setup ---
    OTEL_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if OTEL_ENDPOINT:
        provider = TracerProvider()
        processor = BatchSpanProcessor(
            OTLPSpanExporter(endpoint=OTEL_ENDPOINT, insecure=True)
        )
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)

        FastAPIInstrumentor.instrument_app(app)
        RequestsInstrumentor().instrument()  # Instrument outgoing requests

        logger.info(f"OpenTelemetry tracing enabled. Exporting to: {OTEL_ENDPOINT}")
    else:
        logger.info(
            "OpenTelemetry tracing is disabled (OTEL_EXPORTER_OTLP_ENDPOINT not set)."
        )
    # --- End Tracing Setup ---

    validate_critical_imports()

    logger.info(
        f"Default KOBOLDCPP_MODEL (fallback for llm_model_name): "
        f"{os.getenv('KOBOLDCPP_MODEL', 'Not Set')}"
    )
    logger.info(
        f"Default KOBOLDCPP_API_URL (used by runtime config): "
        f"{os.getenv('KOBOLDCPP_API_URL', 'Not Set')}"
    )

    logger.info("Importing all available tools...")
    import_all_tools()
    log_registry_contents()

    root_logger = logging.getLogger()
    if not any(isinstance(h, WebSocketLogHandler) for h in root_logger.handlers):
        ws_handler = WebSocketLogHandler()
        ws_handler.setLevel(root_logger.level)
        root_logger.addHandler(ws_handler)
        logger.info("WebSocket log handler configured and attached to root logger.")
    else:
        logger.info("WebSocket log handler already attached.")


@app.on_event("shutdown")
async def on_shutdown():
    """Performs graceful shutdown actions, like closing WebSockets."""
    logger.info("--- AEGIS Application Shutdown ---")
    logger.info(f"Closing {len(connected_clients)} active WebSocket connections...")
    close_tasks = [client.close() for client in connected_clients]
    await asyncio.gather(*close_tasks, return_exceptions=True)
    logger.info("All WebSocket connections closed.")


app.include_router(api_router, prefix="/api")
logger.info("All API routes registered under the /api prefix.")

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
    log_level_str = os.getenv("AEGIS_LOG_LEVEL", "info").lower()
    reload_server = os.getenv("AEGIS_RELOAD", "false").lower() == "true"

    numeric_log_level = getattr(logging, log_level_str.upper(), logging.INFO)
    logging.getLogger().setLevel(numeric_log_level)
    logger.info(f"Root logger level set to: {log_level_str.upper()}")

    logger.info(f"Server will run on http://{host}:{port}")
    logger.info(f"Uvicorn log level (for Uvicorn's own logs) set to: {log_level_str}")
    logger.info(f"Hot-reloading enabled: {reload_server}")

    uvicorn.run(
        "aegis.serve_dashboard:app",
        host=host,
        port=port,
        log_level=log_level_str,
        reload=reload_server,
    )
