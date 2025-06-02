"""
Core execution logic for running an agent task using LangGraph.
"""

from aegis.agents.agent_graph import AgentGraph
from aegis.agents.config import AgentGraphConfig, NodeConfig
from aegis.agents.task_state import TaskState
from aegis.schemas.agent import TaskRequest
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


async def run_task(task: TaskRequest) -> str:
    """
    Run a task by constructing and executing an AgentGraph pipeline.

    :param task: A task request containing task_name and task_prompt
    :type task: TaskRequest
    :return: The final task summary string
    :rtype: str
    :raises Exception: if graph building or execution fails
    """
    logger.info(f"Starting agent with task: {task.task_name}")
    config = AgentGraphConfig(
        state_type=TaskState,
        entrypoint="reflect",
        edges=[("reflect", "execute")],
        nodes=[
            NodeConfig(id="reflect", tool="reflect"),
            NodeConfig(id="execute", tool="execute"),
            NodeConfig(id="summarize", tool="summarize"),
        ],
        condition_node="execute",
        condition_map={"success": "summarize", "error": "reflect"},
    )
    try:
        graph = AgentGraph(config).build_graph()
    except (ValueError, TypeError) as e:
        logger.exception(f"Failed to create agent graph: {e}")
        raise

    state = TaskState(task_id=task.task_name, task_prompt=task.task_prompt)
    try:
        result = await graph.ainvoke({"state": state})
        logger.info("Agent execution complete.")
        return result["state"].summary or "[No summary returned]"
    except Exception as e:
        logger.exception(f"Agent graph execution failed: {e}")
        raise
