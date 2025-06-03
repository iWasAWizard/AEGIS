"""
Node function registry for mapping agent step names to their corresponding callables.
Supports aliases for reflective planning, execution, summarization, and termination steps.
"""

from aegis.agents.steps.check_termination import check_termination
from aegis.agents.steps.reflect_and_plan import reflect_and_plan
from aegis.agents.steps.execute_tool import execute_tool
from aegis.agents.steps.summarize_result import summarize_result
from aegis.agents.steps.route_after_tool import route_after_tool
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)

AGENT_NODE_REGISTRY = {
    # Reflective planning step
    "reflect_and_plan": reflect_and_plan,
    "reflect": reflect_and_plan,
    "plan": reflect_and_plan,
    "think": reflect_and_plan,
    "analyze": reflect_and_plan,
    # Routing or decision-making
    "route": route_after_tool,
    "route_after_tool": execute_tool,
    "dispatch": route_after_tool,
    # Tool Execution
    "execute": execute_tool,
    "run": execute_tool,
    "rerun": execute_tool,
    "retry": execute_tool,
    "start": execute_tool,
    "test": execute_tool,
    "use": execute_tool,
    "manipulate": execute_tool,
    "execute_tool": execute_tool,
    # Summarization
    "summarize": summarize_result,
    "summarize_result": summarize_result,
    "report": summarize_result,
    "finalize": summarize_result,
    "brief": summarize_result,
    # Exit conditions
    "terminate": check_termination,
    "end": check_termination,
    "check_termination": check_termination,
    "complete": check_termination,
    "stop": check_termination,
}
