# aegis/agents/steps/summarize_result.py
"""
The final summarization step for the agent's workflow.

This module contains the `summarize_result` function, which is responsible
for creating a comprehensive, human-readable report and then delegating the
creation of the machine-readable provenance log and memory index update.
"""
import json
from pathlib import Path

from aegis.agents.task_state import TaskState
from aegis.utils.logger import setup_logger
from aegis.utils.memory_indexer import update_memory_index
from aegis.utils.provenance import generate_provenance_report

logger = setup_logger(__name__)


def summarize_result(state: TaskState) -> dict:
    """Creates a final summary, saves reports, and triggers follow-up actions.

    This function is called as the last step in a graph before ending. It
    builds a human-readable Markdown report, saves it, and then calls the
    provenance and memory indexing utilities.

    :param state: The final state of the task, containing the complete history.
    :type state: TaskState
    :return: A dictionary containing the final summary text for the API response.
    :rtype: dict
    """
    logger.info("🎬 Step: Summarize Final Result, Save Reports, and Update Memory")
    final_summary = "No actions were taken by the agent."
    reports_dir = Path("reports") / state.task_id
    reports_dir.mkdir(parents=True, exist_ok=True)

    # Part 1: Generate the human-readable summary
    if state.history:
        summary_lines = [
            f"# AEGIS Task Report: {state.task_id}",
            f"**Goal:** {state.task_prompt}\n",
            "---",
        ]
        for i, entry in enumerate(state.history):
            summary_lines.append(f"### Step {i + 1}: {entry.plan.tool_name}")
            summary_lines.append(f"**Thought:** {entry.plan.thought}")
            summary_lines.append(f"**Action:** `{entry.plan.tool_name}` with arguments:")
            summary_lines.append(f"```json\n{json.dumps(entry.plan.tool_args, indent=2)}\n```")
            summary_lines.append("**Observation:**")
            summary_lines.append(f"```\n{str(entry.observation)}\n```\n")
        summary_lines.append("---\n**End of Report.**")
        final_summary = "\n".join(summary_lines)

        summary_path = reports_dir / "summary.md"
        try:
            summary_path.write_text(final_summary, encoding="utf-8")
            logger.info(f"Final report saved to {summary_path}")
        except IOError as e:
            logger.error(f"Failed to save final report to '{summary_path}': {e}")

    # Part 2: Delegate creation of the machine-readable provenance report
    generate_provenance_report(state)

    # Part 3: Trigger the automatic memory index update
    try:
        logger.info("Triggering automatic memory index update...")
        update_memory_index()
    except Exception as e:
        logger.exception(f"Failed to update memory index. Error: {e}")

    # Part 4: Return the final state for the API response
    return {"final_summary": final_summary}
