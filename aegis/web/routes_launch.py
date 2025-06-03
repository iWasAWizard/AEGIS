"""
Launch route for initiating agent tasks via API.
"""

import uuid

from fastapi import APIRouter, HTTPException

from aegis.agents.agent_graph import AgentGraph
from aegis.agents.task_state import TaskState, attach_runtime
from aegis.schemas.agent import TaskRequest
from aegis.schemas.launch_request import LaunchRequest
from aegis.schemas.runtime_execution_config import RuntimeExecutionConfig
from aegis.utils.config_loader import load_agent_config
from aegis.utils.logger import setup_logger
from aegis.utils.llm_query import llm_query

router = APIRouter()
logger = setup_logger(__name__)


@router.post("/launch")
async def launch_task(payload: LaunchRequest):
    """
    Handle task launch requests.

    Constructs the TaskState and AgentGraph, then runs the agent using the provided payload.
    Supports profile-based configuration loading and optional runtime overrides.

    :param payload: LaunchRequest containing task parameters, config override, and optional iteration count.
    :return: Dictionary with task ID and result.
    :raises HTTPException: If the task prompt is empty or an internal error occurs.
    """
    logger.info("→ [routes_launch] Entering def()")

    task: TaskRequest = payload.task
    iterations = payload.iterations or 1

    # Resolve runtime config (from payload.config which may be dict or object)
    if isinstance(payload.config, dict):
        runtime_config = RuntimeExecutionConfig(**payload.config)
    elif isinstance(payload.config, RuntimeExecutionConfig):
        runtime_config = payload.config
    else:
        runtime_config = RuntimeExecutionConfig()

    if not task.task_prompt.strip():
        logger.warning("[launch] Received empty task_prompt")
        raise HTTPException(status_code=400, detail="Task prompt must not be empty")

    try:
        config = load_agent_config(profile=task.profile or "default")
        logger.info(
            f"[config loader] Loaded config profile '{task.profile or 'default'}' successfully."
        )

        state = TaskState(
            task_id=str(uuid.uuid4()),
            task_prompt=task.task_prompt,
            safe_mode=runtime_config.safe_mode,
            runtime=runtime_config,
        )

        attach_runtime(state, llm_query_fn=llm_query)

        logger.info(
            f"[launch] Launching task {state.task_id} with prompt: {state.task_prompt}"
        )
        graph = AgentGraph(config)
        result = await graph.run(state)

        return {"task_id": state.task_id, "result": result}

    except Exception as e:
        logger.error(f"[launch] Agent execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
