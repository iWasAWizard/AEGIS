# aegis/web/routes_launch.py
"""
The primary API route for launching agent tasks.
"""

import json
import traceback
import uuid
from typing import Dict

from fastapi import APIRouter, HTTPException
from langgraph.errors import GraphInterrupt
from pydantic import ValidationError

from aegis.agents.agent_graph import AgentGraph
from aegis.agents.task_state import TaskState
from aegis.exceptions import ConfigurationError, PlannerError, ToolError
from aegis.schemas.agent import AgentConfig, AgentGraphConfig
from aegis.schemas.api import HistoryStepResponse, LaunchResponse
from aegis.schemas.launch import LaunchRequest
from aegis.utils.config_loader import load_agent_config
from aegis.utils.log_sinks import task_id_context
from aegis.utils.logger import setup_logger

router = APIRouter()
logger = setup_logger(__name__)

# In-memory store for interrupted graph states.
# In a production system, this should be a more persistent store like Redis.
INTERRUPTED_STATES: Dict[str, Dict] = {}


@router.post("/launch", response_model=LaunchResponse)
async def launch_task(payload: LaunchRequest) -> LaunchResponse:
    """Handles an agent task launch request.

    This is the main entry point for running an agent task via the API. It
    receives a `LaunchRequest` payload, which includes the task prompt and
    all configuration. It then orchestrates the agent's execution by:
    1. Generating a unique task ID.
    2. Loading the specified agent configuration preset.
    3. Applying any runtime overrides.
    4. Initializing the agent's state.
    5. Building and invoking the execution graph.
    6. Returning the final result or a detailed error.

    :param payload: The launch request containing the task and configuration.
    :type payload: LaunchRequest
    :return: A dictionary containing the task ID, final summary, and history.
    :rtype: dict
    :raises HTTPException: If there is a configuration, planning, or tool error.
    """
    task_id = payload.task.task_id or str(uuid.uuid4())
    task_id_context.set(task_id)
    logger.info(f"🚀 Received launch request for task: '{payload.task.prompt[:50]}...'")
    logger.debug(f"Full launch payload received: {payload.model_dump_json(indent=2)}")

    try:
        preset_config: AgentConfig = load_agent_config(
            profile=payload.config if isinstance(payload.config, str) else None,
            raw_config=payload.config if isinstance(payload.config, dict) else None,
        )
        runtime_config = preset_config.runtime
        if payload.execution:
            runtime_config = runtime_config.model_copy(
                update=payload.execution.model_dump(exclude_unset=True)
            )
        if payload.iterations is not None:
            runtime_config.iterations = payload.iterations

        # Added detailed logging for the final runtime configuration
        logger.debug(
            f"Final runtime configuration for task {task_id}:\n"
            f"{runtime_config.model_dump_json(indent=2)}"
        )

        initial_state = TaskState(
            task_id=task_id, task_prompt=payload.task.prompt, runtime=runtime_config
        )

        graph_structure = AgentGraphConfig(
            state_type=preset_config.state_type,
            entrypoint=preset_config.entrypoint,
            nodes=preset_config.nodes,
            edges=preset_config.edges,
            condition_node=preset_config.condition_node,
            condition_map=preset_config.condition_map,
            middleware=preset_config.middleware,
            interrupt_nodes=preset_config.interrupt_nodes,
        )

        agent_graph = AgentGraph(graph_structure).build_graph()

        final_state_dict = await agent_graph.ainvoke(initial_state.model_dump())
        final_state = TaskState(**final_state_dict)

        # After the graph has run, check if the last action was an interruption
        if (
            final_state.history
            and final_state.history[-1].plan.tool_name == "ask_human_for_input"
        ):
            logger.info(f"⏸️  Task {task_id} has been paused for human input.")
            # Store the compiled graph and the interrupted state for later resumption.
            INTERRUPTED_STATES[task_id] = {
                "graph": agent_graph,
                "state": final_state.model_dump(),
            }
            last_observation = final_state.history[-1].observation
            return LaunchResponse(
                task_id=task_id,
                summary=last_observation,
                status="PAUSED",
                history=[],
            )

        logger.info(f"✅ Task {task_id} completed successfully.")

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

    except ValidationError as e:
        logger.error(f"Pydantic validation failed during task launch: {e}")
        error_details = "\n".join(
            [f"  - {err['loc']}: {err['msg']}" for err in e.errors()]
        )
        logger.error(f"Validation error details:\n{error_details}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid Configuration: Pydantic validation failed. Check server logs for details.",
        )
    except ConfigurationError as e:
        logger.error(f"Configuration error during task launch: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid Configuration: {e}")
    except (PlannerError, ToolError) as e:
        logger.error(f"Agent execution error: {e}")
        logger.debug(f"Traceback:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Agent Execution Failed: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred during launch: {e}")
        logger.debug(f"Traceback:\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {e.__class__.__name__}: {e}",
        )
