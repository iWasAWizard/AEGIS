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
from typing import Optional

# A context variable to hold the current task_id. This allows loggers
# anywhere in the call stack to access the task_id without it being
# passed down as an argument.
task_id_context: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "task_id", default=None
)


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
    A logging handler that writes structured JSON records to a task-specific
    file in a "JSON Lines" (.jsonl) format.
    """

    def __init__(self, logs_dir: str):
        """Initializes the handler with the target directory for logs.

        :param logs_dir: The directory where log files will be stored.
        :type logs_dir: str
        """
        super().__init__()
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.addFilter(TaskIdFilter())
        # The formatter for this handler will be set in the main logger setup.

    def emit(self, record: logging.LogRecord):
        """Writes the log record to the appropriate file if a task_id is present.

        :param record: The log record to be emitted.
        :type record: logging.LogRecord
        """
        task_id = getattr(record, "task_id", None)
        if not task_id:
            # If there's no task_id, we don't write to a file.
            # These are system-level logs that go to the console/other handlers.
            return

        try:
            log_file = self.logs_dir / f"{task_id}.jsonl"
            # The self.format() method correctly uses the formatter assigned to the handler.
            # For this handler, it will be a JsonFormatter instance.
            json_log_string = self.format(record)
            with log_file.open("a", encoding="utf-8") as f:
                f.write(json_log_string + "\n")
        except Exception:
            self.handleError(record)
