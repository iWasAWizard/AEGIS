"""
Launch route for initiating agent tasks via API.
"""

import uuid

from fastapi import APIRouter, HTTPException

from aegis.agents.agent_graph import AgentGraph
from aegis.agents.task_state import TaskState, attach_runtime
from aegis.schemas.agent import TaskRequest
from aegis.schemas.launch_request import LaunchRequest
from aegis.utils.config_loader import load_agent_config
from aegis.utils.llm_query import llm_query
from aegis.utils.logger import setup_logger

router = APIRouter()
logger = setup_logger(__name__)


@router.post("/launch")
async def launch_task(payload: LaunchRequest):
    """
    launch_task.
    :param payload: Description of payload
    :type payload: Any
    :return: Description of return value
    :rtype: Any
    """
    logger.info("→ [routes_launch] Entering def()")
    task: TaskRequest = payload.task
    config_override = payload.config
    iterations = payload.iterations or 1
    if not task.task_prompt.strip():
        logger.warning("[launch] Received empty prompt.")
        raise HTTPException(status_code=400, detail="Prompt must not be empty.")
    task_id = str(uuid.uuid4())[:8]
    logger.info(f"[launch] Launching task {task_id} with prompt: {task.task_prompt}")
    logger.debug(f"[launch] Max iterations: {iterations}")
    try:
        config = load_agent_config(profile=task.profile, raw_config=config_override)
    except Exception as e:
        logger.error(f"[launch] Invalid config or profile: {e}")
        raise HTTPException(status_code=400, detail="Invalid agent configuration.")
    task_state = TaskState(task_id=task_id, task_prompt=task.task_prompt)
    initial_state = attach_runtime(task_state, llm_query_fn=llm_query)

    try:
        state_dict = initial_state.model_dump()
        logger.debug(f"Serialized TaskState: {state_dict}")
        result = await AgentGraph(config).run(state_dict)
        logger.info(f"[launch] Task {task_id} execution complete")
        return {
            "status": "success",
            "task_id": task_id,
            "summary": result["state"].summary,
            "iterations": iterations,
        }
    except Exception as e:
        logger.exception(f"[launch] Agent execution failed: {e}")
        raise HTTPException(status_code=500, detail=f"Task execution failed: {e}")
