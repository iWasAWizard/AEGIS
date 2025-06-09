# aegis/web/routes_launch.py
"""
The primary API route for launching agent tasks.
"""

import traceback
import uuid

from fastapi import APIRouter, HTTPException

from aegis.agents.agent_graph import AgentGraph
from aegis.agents.task_state import TaskState
from aegis.schemas.agent import AgentConfig, AgentGraphConfig
from aegis.schemas.launch import LaunchRequest
from aegis.utils.config_loader import load_agent_config
from aegis.utils.log_sinks import task_id_context
from aegis.utils.logger import setup_logger

router = APIRouter()
logger = setup_logger(__name__)


@router.post("/launch", response_model=dict)
async def launch_task(payload: LaunchRequest) -> dict:
    """Handles an agent task launch request.

    This endpoint constructs the full agent state, builds the execution graph
    based on the specified configuration, and invokes the agent. It returns
    the final state of the task, including the summary and history.

    :param payload: The launch request containing the task, config, and overrides.
    :type payload: LaunchRequest
    :return: A dictionary containing the final task summary and a unique task ID.
    :rtype: dict
    :raises HTTPException: If agent execution fails.
    """
    task_id = payload.task.task_id or str(uuid.uuid4())
    task_id_context.set(task_id)

    logger.info(f"🚀 Received launch request for task: '{payload.task.prompt[:50]}...'")

    try:
        # Load the full preset, which is an AgentConfig object
        preset_config: AgentConfig = load_agent_config(
            profile=payload.config if isinstance(payload.config, str) else None,
            raw_config=payload.config if isinstance(payload.config, dict) else None,
        )

        # Start with the runtime config from the loaded preset
        runtime_config = preset_config.runtime

        # Apply overrides from the launch payload
        if payload.execution:
            runtime_config = runtime_config.model_copy(
                update=payload.execution.model_dump(exclude_unset=True)
            )

        if payload.iterations is not None:
            runtime_config.iterations = payload.iterations

        # Initialize the state with the final, merged runtime config
        initial_state = TaskState(
            task_id=task_id,
            task_prompt=payload.task.prompt,
            runtime=runtime_config,
        )

        # Build the graph using only the graph-related parts of the preset
        graph_structure = AgentGraphConfig(**preset_config.model_dump())
        agent_graph = AgentGraph(graph_structure).build_graph()

        final_state_dict = await agent_graph.ainvoke(initial_state)

        # Extract the final summary for the response
        final_state = TaskState(**final_state_dict)
        logger.info(f"✅ Task {task_id} completed successfully.")

        return {
            "task_id": task_id,
            "summary": final_state.final_summary,
            "history": [
                {
                    "thought": scratchpad.thought,
                    "tool_name": scratchpad.tool_name,
                    "tool_args": scratchpad.tool_args,
                    "tool_output": str(output),
                }
                for scratchpad, output in final_state.history
            ],
        }

    except Exception as e:
        logger.error(f"Agent execution failed: {e}")
        logger.debug(f"Traceback:\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Agent execution failed: {e.__class__.__name__}: {e}",
        )
