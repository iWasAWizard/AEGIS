# aegis/utils/log_sinks.py
"""
Custom logging components for the AEGIS framework.

This module provides specialized logging Sinks (Handlers) and Filters to create
a unified event bus. It enables structured, context-aware logging that can be
routed to multiple destinations (console, file, UI) from a single log call.
"""
import contextvars
import json
import logging
from pathlib import Path
from typing import Dict, Any

# A context variable to hold the current task_id. This allows loggers
# anywhere in the call stack to access the task_id without it being
# passed down as an argument.
task_id_context = contextvars.ContextVar("task_id", default=None)


class TaskIdFilter(logging.Filter):
    """
    A logging filter that injects the current task_id from the contextvar
    into the log record.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Adds the task_id to the log record if it exists in the context.

        :param record: The log record being processed.
        :type record: logging.LogRecord
        :return: Always returns True to allow the record to be processed.
        :rtype: bool
        """
        record.task_id = task_id_context.get()
        return True


class JsonlFileHandler(logging.Handler):
    """
    A logging handler that writes structured log events to a task-specific
    JSONL file.

    This handler checks for a `task_id` on each log record. If one is present,
    it writes a JSON object representing the log event to `logs/{task_id}.jsonl`.
    This creates a machine-readable audit trail for every task run.
    """

    def __init__(self, logs_dir: str = "logs"):
        """Initializes the handler, creating the logs directory if needed.

        :param logs_dir: The base directory where task log files will be stored.
        :type logs_dir: str
        """
        super().__init__()
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(exist_ok=True)
        self.addFilter(TaskIdFilter())

    def emit(self, record: logging.LogRecord) -> None:
        """
        Formats the log record as JSON and writes it to the appropriate file.

        If the log record has no `task_id`, this method does nothing. Otherwise,
        it constructs a JSON object containing standard log fields and any
        structured `extra` data, then appends it as a new line to the
        corresponding task's log file.

        :param record: The log record to process.
        :type record: logging.LogRecord
        """
        # Safely get the task_id attribute, defaulting to None if it doesn't exist.
        task_id = getattr(record, "task_id", None)

        # We only want to write to the file if a task is active.
        if not task_id:
            return

        # The 'extra_data' attribute is where our structured data lives.
        # We'll augment it with standard log info.
        log_entry: Dict[str, Any] = {
            "timestamp": logging.Formatter().formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger_name": record.name,
        }

        # If the log call included structured data in 'extra_data', merge it in.
        # The StructuredLoggerAdapter wraps this in 'extra_data'.
        if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):  # type: ignore
            log_entry.update(record.extra_data)  # type: ignore

        log_path = self.logs_dir / f"{task_id}.jsonl"

        try:
            with log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception:
            self.handleError(record)
