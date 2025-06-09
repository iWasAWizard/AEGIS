# aegis/agents/steps/summarize_result.py
"""
The final summarization step for the agent's workflow.

This module contains the `summarize_result` function, which is responsible
for creating a comprehensive, human-readable report of the agent's entire
execution history and then triggering the memory index update.
"""
import json
import os

from aegis.agents.task_state import TaskState
from aegis.utils.logger import setup_logger
from aegis.utils.memory_indexer import update_memory_index

logger = setup_logger(__name__)


def summarize_result(state: TaskState) -> dict:
    """
    Creates a final summary and triggers the memory index update.
    This function is called as the last step in a graph before ending.
    """
    logger.info("🎬 Step: Summarize Final Result and Update Memory")

    # Part 1: Generate the human-readable summary
    if not state.history:
        summary = "No actions were taken by the agent."
    else:
        summary_lines = [
            f"# AEGIS Task Report: {state.task_id}",
            f"**Goal:** {state.task_prompt}\n",
            "---",
        ]

        for i, (scratchpad, result) in enumerate(state.history):
            summary_lines.append(f"### Step {i + 1}: {scratchpad.tool_name}")
            summary_lines.append(f"**Thought:** {scratchpad.thought}")
            summary_lines.append(
                f"**Action:** `{scratchpad.tool_name}` with arguments:"
            )
            summary_lines.append(
                f"```json\n{json.dumps(scratchpad.tool_args, indent=2)}\n```"
            )
            summary_lines.append("**Observation:**")
            summary_lines.append(f"```\n{str(result)}\n```\n")

        summary_lines.append("---\n**End of Report.**")
        final_summary = "\n".join(summary_lines)

        # Save summary to file for posterity
        reports_dir = Path("reports") / state.task_id
        reports_dir.mkdir(parents=True, exist_ok=True)
        summary_path = reports_dir / "summary.md"
        summary_path.write_text(final_summary, encoding="utf-8")
        logger.info(f"Final report saved to {summary_path}")

    # Part 2: Trigger the automatic memory index update
    # This happens synchronously and will block the API return slightly, but
    # ensures memory is always up-to-date for the next task.
    update_memory_index()

    # Part 3: Return the final state for the API response
    return {"final_summary": final_summary if "final_summary" in locals() else summary}
