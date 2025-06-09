# aegis/tests/utils/test_provenance.py
"""
Unit tests for the provenance reporting utility.
"""
import json
import os
import time
from pathlib import Path

import pytest

from aegis.agents.task_state import HistoryEntry, TaskState
from aegis.schemas.runtime import RuntimeExecutionConfig
from aegis.utils.provenance import generate_provenance_report, _get_final_status
from schemas.plan_output import AgentScratchpad


@pytest.fixture
def sample_history() -> list[HistoryEntry]:
    """Provides a sample list of HistoryEntry objects for testing."""
    plan1 = AgentScratchpad(thought="Step 1 thought", tool_name="tool_one", tool_args={"arg": 1})
    entry1 = HistoryEntry(
        plan=plan1,
        observation="Output 1",
        status="success",
        start_time=time.time() - 10,
        end_time=time.time() - 8,
        duration_ms=2000,
    )

    plan2 = AgentScratchpad(thought="Step 2 thought", tool_name="tool_two", tool_args={"arg": 2})
    entry2 = HistoryEntry(
        plan=plan2,
        observation="[ERROR] Something failed",
        status="failure",
        start_time=time.time() - 5,
        end_time=time.time() - 4,
        duration_ms=1000,
    )

    return [entry1, entry2]


@pytest.mark.parametrize(
    "last_tool_name, last_tool_args, last_status, expected_overall_status",
    [
        ("finish", {"status": "success"}, "success", "SUCCESS"),
        ("finish", {"status": "failure"}, "success", "FAILURE"),
        ("finish", {"status": "partial"}, "success", "PARTIAL"),
        ("some_other_tool", {}, "success", "PARTIAL"),  # Ended without explicit finish
        ("some_other_tool", {}, "failure", "FAILURE"),  # Ended on a failed step
    ]
)
def test_get_final_status(last_tool_name, last_tool_args, last_status, expected_overall_status):
    """Tests the _get_final_status helper with various end-of-task scenarios."""
    plan = AgentScratchpad(thought="last step", tool_name=last_tool_name, tool_args=last_tool_args)
    entry = HistoryEntry(plan=plan, observation="", status=last_status)
    state = TaskState(task_id="test", task_prompt="test", runtime=RuntimeExecutionConfig(), history=[entry])

    assert _get_final_status(state) == expected_overall_status


def test_get_final_status_no_action():
    """Tests that the status is NO_ACTION if the history is empty."""
    state = TaskState(task_id="test", task_prompt="test", runtime=RuntimeExecutionConfig(), history=[])
    assert _get_final_status(state) == "NO_ACTION"


def test_generate_provenance_report(tmp_path: Path, sample_history: list[HistoryEntry]):
    """
    Tests that a valid provenance.json file is created and contains the correct data.
    """
    task_id = "provenance-test-123"
    state = TaskState(
        task_id=task_id,
        task_prompt="A test prompt",
        runtime=RuntimeExecutionConfig(),
        history=sample_history,
    )

    # Change CWD so the report is written to the temp directory
    original_cwd = Path.cwd()
    os.chdir(tmp_path)

    try:
        generate_provenance_report(state)

        report_path = Path("reports") / task_id / "provenance.json"
        assert report_path.is_file(), "Provenance report file was not created."

        with report_path.open("r") as f:
            data = json.load(f)

        assert data["task_id"] == task_id
        assert data["task_prompt"] == "A test prompt"
        assert data["final_status"] == "FAILURE"  # Based on the last entry in sample_history
        assert len(data["events"]) == 2

        # Check an event entry
        event1 = data["events"][0]
        assert event1["step"] == 1
        assert event1["status"] == "success"
        assert event1["tool_name"] == "tool_one"
        assert "duration_ms" in event1

    finally:
        # Restore the original working directory
        os.chdir(original_cwd)
