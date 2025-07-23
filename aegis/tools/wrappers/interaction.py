# aegis/agents/steps/interaction.py
"""
Agent steps related to human-in-the-loop interaction.
"""
import time
from typing import Dict, Any

from aegis.agents.task_state import HistoryEntry, TaskState
from aegis.schemas.plan_output import AgentScratchpad
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


def process_human_feedback(state: TaskState) -> Dict[str, Any]:
    """
    Processes human feedback from the state and adds it to the history.
    This node runs after a graph interruption is resumed.
    """
    logger.info("🗣️ Step: Process Human Feedback")
    if state.human_feedback is None:
        logger.warning(
            "process_human_feedback called but no human feedback found in state."
        )
        return {}

    feedback_entry = HistoryEntry(
        plan=AgentScratchpad(
            thought="The agent paused to ask for human guidance. Now, I will incorporate the provided feedback into my plan.",
            tool_name="process_human_feedback",
            tool_args={},
        ),
        observation=f"Human provided the following input: '{state.human_feedback}'",
        status="success",
        start_time=time.time(),
        end_time=time.time(),
    )

    # Return the updated history and clear the feedback from the state
    return {
        "history": state.history + [feedback_entry],
        "human_feedback": None,
    }
