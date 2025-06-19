# aegis/schemas/node_registry.py
"""
Node function registry for mapping agent step names to their callables.

This dictionary acts as a dispatcher, allowing graph configurations in YAML
to refer to agent step functions by a simple name. It maps the string IDs
used in the `nodes` list of a preset to the actual Python functions that
implement the agent's logic. This is the single source of truth for all
functions that can act as nodes in an agent's execution graph.
"""

from typing import Dict, Callable, Any

from aegis.agents.steps.check_termination import check_termination
from aegis.agents.steps.execute_tool import execute_tool
from aegis.agents.steps.reflect_and_plan import reflect_and_plan
from aegis.agents.steps.summarize_result import summarize_result
from aegis.agents.steps.verification import (
    remediate_plan,
    verify_outcome,
    route_after_verification,
)
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)
logger.info("Initializing aegis.schemas.node_registry module...")

# This registry maps the `tool` name specified in a preset's `nodes` list
# to the actual function that will be executed for that node.
AGENT_NODE_REGISTRY: Dict[str, Callable[..., Any]] = {
    # The core planning step where the agent uses the LLM to decide what to do next.
    "reflect_and_plan": reflect_and_plan,
    # The step that executes the tool chosen by the planner.
    "execute_tool": execute_tool,
    # The conditional routing step that decides whether to loop or end.
    "check_termination": check_termination,
    # The final step that generates a human-readable summary of the entire task.
    "summarize_result": summarize_result,
    # The step that verifies if the main action was successful.
    "verify_outcome": verify_outcome,
    # The step that creates a recovery plan after a failure.
    "remediate_plan": remediate_plan,
    # The new central router for the verification flow.
    "route_after_verification": route_after_verification,
}

logger.info(
    f"Agent node registry initialized with keys: {list(AGENT_NODE_REGISTRY.keys())}"
)
