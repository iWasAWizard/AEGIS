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
        """Adds the task_id to the log record."""
        record.task_id = task_id_context.get()
        return True


class JsonlFileHandler(logging.Handler):
    """
    A logging handler that writes structured log events to a task-specific
    JSONL file.
    """

    def __init__(self, logs_dir: str = "logs"):
        """Initializes the handler."""
        super().__init__()
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(exist_ok=True)
        self.addFilter(TaskIdFilter())  # Ensure task_id is always available

    def emit(self, record: logging.LogRecord) -> None:
        """
        Writes the log record to the appropriate JSONL file if it is a
        structured event.
        """
        # We only want to write to the file if a task is active.
        if not hasattr(record, "task_id") or not record.task_id:
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
        if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):
            log_entry.update(record.extra_data)

        log_path = self.logs_dir / f"{record.task_id}.jsonl"

        try:
            with log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception:
            self.handleError(record)
