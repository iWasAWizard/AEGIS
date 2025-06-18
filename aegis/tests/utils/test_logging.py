# aegis/tests/utils/test_logging.py
"""
Unit tests for the custom logging infrastructure.
"""
import json
import logging
from pathlib import Path

import pytest

from aegis.utils.log_sinks import JsonlFileHandler, TaskIdFilter, task_id_context


@pytest.fixture
def setup_test_logger(tmp_path: Path):
    """Sets up an isolated logger with our custom handlers for testing."""
    # Use a unique logger name to avoid interfering with the root logger
    logger = logging.getLogger("test_logger")
    logger.setLevel(logging.DEBUG)

    # Clear any existing handlers from previous tests
    if logger.hasHandlers():
        logger.handlers.clear()

    # Create a handler that writes to a temp directory
    handler = JsonlFileHandler(logs_dir=str(tmp_path))
    logger.addHandler(handler)

    yield logger

    # Teardown: clear handlers and reset context
    logger.handlers.clear()
    task_id_context.set(None)


def test_task_id_filter():
    """Verify the TaskIdFilter correctly injects the task_id into a LogRecord."""
    task_id_filter = TaskIdFilter()
    record = logging.LogRecord(name="test", level=logging.INFO, pathname="", lineno=0, msg="", args=(), exc_info=None)

    # Case 1: Context is not set
    task_id_context.set(None)
    task_id_filter.filter(record)
    assert record.task_id is None

    # Case 2: Context is set
    task_id_context.set("test-123")
    task_id_filter.filter(record)
    assert record.task_id == "test-123"


def test_jsonl_file_handler_with_task_id(setup_test_logger, tmp_path: Path):
    """Verify that a structured log is written to the correct task-specific JSONL file."""
    logger = setup_test_logger
    task_id = "task-for-logging"
    task_id_context.set(task_id)

    log_message = "Executing tool."
    extra_data = {"event_type": "ToolStart", "tool_name": "test_tool"}

    logger.info(log_message, extra=extra_data)

    log_file_path = tmp_path / f"{task_id}.jsonl"
    assert log_file_path.is_file(), "Log file was not created."

    # Read the content and verify it's valid JSON with the correct data
    with log_file_path.open("r") as f:
        log_entry = json.loads(f.read())

    assert log_entry["level"] == "INFO"
    assert log_entry["message"] == log_message
    assert log_entry["logger_name"] == "test_logger"
    assert log_entry["event_type"] == "ToolStart"
    assert log_entry["tool_name"] == "test_tool"


def test_jsonl_file_handler_no_task_id(setup_test_logger, tmp_path: Path):
    """Verify that the handler does not write a file if no task_id is in the context."""
    logger = setup_test_logger
    task_id_context.set(None)

    logger.info("This is a system-level log without a task ID.")

    # Check that NO files were created in the log directory
    log_files = list(tmp_path.glob("*.jsonl"))
    assert len(log_files) == 0, "Log file should not have been created without a task_id."
