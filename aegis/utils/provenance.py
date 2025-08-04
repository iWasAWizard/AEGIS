# aegis/utils/provenance.py
"""
Utility for generating and saving a machine-readable provenance report.

This module encapsulates the logic for creating a detailed, structured JSON
log of an agent's entire execution, providing a complete audit trail for
reproducibility and analysis.
"""
import json
import platform
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, Any

from aegis.agents.task_state import TaskState
from aegis.utils.config import get_config
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)

config = get_config()
REPORTS_BASE_DIR = Path(config.get("paths", {}).get("reports", "reports"))


def _get_final_status(state: TaskState) -> str:
    """Determines the overall task status based on the final step.

    This helper function inspects the last entry in the agent's history to
    determine a final, summary status for the entire task.

    :param state: The final state of the task.
    :type state: TaskState
    :return: A summary status string (e.g., 'SUCCESS', 'FAILURE').
    :rtype: str
    """
    if not state.history:
        return "NO_ACTION"

    last_entry = state.history[-1]
    if last_entry.plan.tool_name == "finish":
        # The 'status' arg in the finish tool determines the outcome
        return last_entry.plan.tool_args.get("status", "UNKNOWN").upper()

    # If the task ended for other reasons (e.g., max iterations)
    if last_entry.status == "failure":
        return "FAILURE"

    # If it ended on a successful step but not via 'finish', it's partial.
    return "PARTIAL"


def _calculate_tool_performance(state: TaskState) -> Dict[str, Any]:
    """Calculates performance metrics for each tool used in the task.

    :param state: The final state of the task.
    :type state: TaskState
    :return: A dictionary of performance metrics for each tool.
    :rtype: Dict[str, Any]
    """
    performance_data = defaultdict(
        lambda: {
            "call_count": 0,
            "success_count": 0,
            "failure_count": 0,
            "total_duration_ms": 0.0,
            "average_duration_ms": 0.0,
        }
    )

    for entry in state.history:
        tool_name = entry.plan.tool_name
        stats = performance_data[tool_name]
        stats["call_count"] += 1
        stats["total_duration_ms"] += entry.duration_ms
        if entry.status == "success":
            stats["success_count"] += 1
        else:
            stats["failure_count"] += 1

    # Calculate averages
    for tool_name, stats in performance_data.items():
        if stats["call_count"] > 0:
            stats["average_duration_ms"] = round(
                stats["total_duration_ms"] / stats["call_count"], 2
            )

    return dict(performance_data)


def generate_provenance_report(state: TaskState):
    """
    Generates and saves a machine-readable JSON report of the agent's execution.

    This function creates a comprehensive `provenance.json` file in the task's
    report directory. This file serves as a "flight data recorder" for the
    agent, capturing the task prompt, final status, environment details, and a
    detailed timeline of every event (thought, action, observation) with
    timestamps and durations. It also includes a performance summary for all
    tools used.

    :param state: The final `TaskState` of the completed agent run.
    :type state: TaskState
    """
    reports_dir = REPORTS_BASE_DIR / state.task_id
    reports_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Generating provenance report...")

    events = []
    for i, entry in enumerate(state.history):
        event_data = {
            "step": i + 1,
            "start_time_utc": time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", time.gmtime(entry.start_time)
            ),
            "duration_ms": round(entry.duration_ms, 2),
            "status": entry.status,
            "thought": entry.plan.thought,
            "tool_name": entry.plan.tool_name,
            "tool_args": entry.plan.tool_args,
            "observation": str(entry.observation),  # Ensure observation is stringified
        }
        events.append(event_data)

    provenance_data = {
        "task_id": state.task_id,
        "task_prompt": state.task_prompt,
        "final_status": _get_final_status(state),
        "steps_taken": len(events),
        "execution_env": {
            "platform": platform.system(),
            "node": platform.node(),
            "python_version": platform.python_version(),
        },
        "tool_performance": _calculate_tool_performance(state),
        "events": events,
    }

    provenance_path = reports_dir / "provenance.json"
    try:
        with provenance_path.open("w", encoding="utf-8") as f:
            json.dump(provenance_data, f, indent=2)
        logger.info(f"Provenance report saved successfully to: {provenance_path}")
    except IOError as e:
        logger.error(f"Failed to save provenance report to '{provenance_path}': {e}")
