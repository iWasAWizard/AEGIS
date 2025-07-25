# aegis/web/routes_evals.py
"""
API routes for managing and running the evaluation suite.
"""
import asyncio

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from aegis.utils.logger import setup_logger

router = APIRouter(prefix="/evals", tags=["Evaluation"])
logger = setup_logger(__name__)


class RunEvalsRequest(BaseModel):
    dataset_name: str
    judge_model: str


async def run_eval_background_task(dataset_name: str, judge_model: str):
    """The async function that runs the evaluation in the background."""
    logger.info(f"Starting background evaluation run for dataset: '{dataset_name}'...")
    try:
        from aegis.evaluation.eval_runner import main as run_eval_main

        await run_eval_main(dataset_name, judge_model)
        logger.info(f"Background evaluation run for '{dataset_name}' completed.")
    except Exception as e:
        logger.exception(f"Background evaluation run for '{dataset_name}' failed: {e}")


@router.post("/run")
def run_evals_endpoint(payload: RunEvalsRequest, background_tasks: BackgroundTasks):
    """
    Kicks off an evaluation suite run as a background task.
    Returns immediately with a 202 Accepted response.
    """
    logger.info(
        f"Received request to run evaluations for dataset: '{payload.dataset_name}'"
    )
    background_tasks.add_task(
        run_eval_background_task, payload.dataset_name, payload.judge_model
    )
    return {
        "status": "accepted",
        "message": f"Evaluation run for dataset '{payload.dataset_name}' has been started in the background.",
    }
