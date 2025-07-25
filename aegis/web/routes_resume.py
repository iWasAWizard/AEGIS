# aegis/web/routes_resume.py
"""
API route for resuming an interrupted agent task.
"""
import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from aegis.agents.task_state import TaskState
from aegis.schemas.api import HistoryStepResponse, LaunchResponse
from aegis.utils.log_sinks import task_id_context
from aegis.utils.logger import setup_logger
from aegis.web.routes_launch import INTERRUPTED_STATES

router = APIRouter()
logger = setup_logger(__name__)


class ResumeRequest(BaseModel):
    task_id: str
    human_feedback: str


@router.post("/resume", response_model=LaunchResponse)
async def resume_task(payload: ResumeRequest):
    """Handles a request to resume a paused agent task with human feedback."""
    task_id = payload.task_id
    task_id_context.set(task_id)
    logger.info(f"▶️ Received resume request for task: {task_id}")

    interrupted_session = INTERRUPTED_STATES.pop(task_id, None)
    if not interrupted_session:
        raise HTTPException(status_code=404, detail="Paused task not found.")

    agent_graph = interrupted_session["graph"]
    saved_state_dict = interrupted_session["state"]

    # Inject the human feedback into the state dictionary
    saved_state_dict["human_feedback"] = payload.human_feedback

    try:
        # Continue the graph execution from the saved state
        final_state_dict = await agent_graph.ainvoke(saved_state_dict)
        final_state = TaskState(**final_state_dict)
        logger.info(f"✅ Resumed task {task_id} completed successfully.")

        # This response structure should match the one from the /launch endpoint
        return LaunchResponse(
            task_id=task_id,
            summary=final_state.final_summary,
            history=[
                HistoryStepResponse(
                    thought=entry.plan.thought,
                    tool_name=entry.plan.tool_name,
                    tool_args=entry.plan.tool_args,
                    tool_output=entry.observation,
                )
                for entry in final_state.history
            ],
        )
    except Exception as e:
        logger.error(f"An unexpected error occurred during task resumption: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to resume task: {e}")
