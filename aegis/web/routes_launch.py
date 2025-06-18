# aegis/web/routes_launch.py
"""
The primary API route for launching agent tasks.
"""

import json
import traceback
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from aegis.agents.agent_graph import AgentGraph
from aegis.agents.task_state import TaskState
from aegis.exceptions import ConfigurationError, PlannerError, ToolError
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
        )

        agent_graph = AgentGraph(graph_structure).build_graph()
        final_state_dict = await agent_graph.ainvoke(initial_state.model_dump())
        final_state = TaskState(**final_state_dict)

        logger.info(f"✅ Task {task_id} completed successfully.")

        logger.info(
            f"🕵️  Inspecting final agent state for task {task_id} before serialization..."
        )
        logger.info(
            f"Final summary type: {type(final_state.final_summary)}, value: {repr(final_state.final_summary)}"
        )
        for i, entry in enumerate(final_state.history):
            logger.info(f"--- History Entry {i} ---")
            logger.info(f"Plan: {repr(entry.plan)}")
            logger.info(
                f"Observation type: {type(entry.observation)}, value: {repr(entry.observation)}"
            )
        logger.info(f"🕵️  State inspection for task {task_id} complete.")

        return {
            "task_id": task_id,
            "summary": final_state.final_summary,
            "history": [
                {
                    "thought": entry.plan.thought,
                    "tool_name": entry.plan.tool_name,
                    "tool_args": json.loads(
                        json.dumps(entry.plan.tool_args, default=str)
                    ),
                    "tool_output": str(entry.observation),
                }
                for entry in final_state.history
            ],
        }

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
