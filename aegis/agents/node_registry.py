"""
Node function registry for mapping agent step names to their corresponding callables.
Supports aliases for reflective planning, execution, summarization, and termination steps.
"""

from aegis.agents.steps.check_termination import check_termination
from aegis.agents.steps.reflect_and_plan import reflect_and_plan
from aegis.agents.steps.route_execution import route_execution
from aegis.agents.steps.summarize_result import summarize_result
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)

AGENT_NODE_REGISTRY = {
    # Reflective planning step
    "reflect": reflect_and_plan,
    "plan": reflect_and_plan,
    "think": reflect_and_plan,
    "analyze": reflect_and_plan,
    # Routing or decision-making
    "route": route_execution,
    "route_execution": route_execution,
    "dispatch": route_execution,
    # Summarization
    "summarize": summarize_result,
    "summarize_result": summarize_result,
    "report": summarize_result,
    "finalize": summarize_result,
    # Exit conditions
    "terminate": check_termination,
    "end": check_termination,
    "check_termination": check_termination,
    "complete": check_termination,
}
