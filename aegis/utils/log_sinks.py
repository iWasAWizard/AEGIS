# aegis/utils/log_sinks.py
"""
Custom logging components for the AEGIS framework.

This module provides specialized logging Sinks (Handlers) and Filters to create
a unified event bus. It enables structured, context-aware logging that can be
routed to multiple destinations (console, file, UI) from a single log call.
"""
import contextvars
import logging

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
