# aegis/web/routes_resume.py
"""
API route for resuming an interrupted agent task.
"""
import json
import traceback

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from aegis.agents.agent_graph import AgentGraph
from aegis.agents.task_state import TaskState
from aegis.executors.redis_exec import RedisExecutor
from aegis.schemas.agent import AgentGraphConfig, AgentConfig
from aegis.schemas.api import HistoryStepResponse, LaunchResponse
from aegis.utils.config_loader import load_agent_config
from aegis.utils.log_sinks import task_id_context
from aegis.utils.logger import setup_logger

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

    try:
        redis = RedisExecutor()
        session_json = redis.get_value(f"aegis:interrupted:{task_id}")
        if "No value found" in session_json:
            raise HTTPException(
                status_code=404, detail="Paused task not found in Redis."
            )

        # Clean up immediately to prevent re-entry attacks or stale state
        redis.delete_value(f"aegis:interrupted:{task_id}")

        session_data = json.loads(session_json)
        saved_state_dict = session_data["state"]
        profile = session_data.get("profile")
        raw_config = session_data.get("raw_config")

        # Re-build the graph config and graph, just like in the launch endpoint
        preset_config = load_agent_config(profile=profile, raw_config=raw_config)
        graph_structure = AgentGraphConfig(**preset_config.model_dump())
        agent_graph = AgentGraph(graph_structure).build_graph()

        # Inject the human feedback into the state dictionary before resuming
        saved_state_dict["human_feedback"] = payload.human_feedback

        # Continue the graph execution from the saved state
        final_state_dict = await agent_graph.ainvoke(saved_state_dict)
        final_state = TaskState(**final_state_dict)
        logger.info(f"✅ Resumed task {task_id} completed successfully.")

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
        logger.debug(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to resume task: {e}")
