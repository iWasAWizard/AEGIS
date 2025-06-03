"""
Command-line interface for running agent tasks from a TaskRequest YAML file.
"""

from pathlib import Path

import typer
import yaml

from aegis.runner import run_task
from aegis.schemas.agent import TaskRequest
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)

app = typer.Typer()


@app.command()
def run(
    task_request_path: str = typer.Option(
        None,
        "--task-request-path",
        help="Path to the YAML file with the TaskRequest",
        prompt="Enter path to the TaskRequest YAML file",
    ),
    safe_mode: bool = typer.Option(
        True, "--safe-mode/--no-safe-mode", help="Run tools in safe mode (recommended)"
    ),
):
    """
    Load a task request from file and run the task using the agent execution engine.
    """
    logger.info(f"Loading TaskRequest from: {task_request_path}")
    try:
        path = Path(task_request_path)
        if not path.exists() or not path.is_file():
            logger.error(f"File not found or invalid: {task_request_path}")
            raise typer.Exit(code=1)
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        task_request = TaskRequest(**data)
    except yaml.YAMLError as e:
        logger.exception(f"YAML parsing failed: {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        logger.exception(f"Failed to load TaskRequest: {e}")
        raise typer.Exit(code=1)
    logger.info(f"Loaded task: {task_request.task_name}")
    logger.info(f"Starting task execution (safe_mode={safe_mode})...")
    try:
        result = run_task(task_request)
        logger.info(f"Task execution complete. Final summary: {result}")
    except Exception as e:
        logger.exception(f"Task execution failed: {e}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
