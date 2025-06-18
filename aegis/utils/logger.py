# aegis/utils/logger.py
"""
Centralized logging setup for the AEGIS framework.

This module configures the root logger with custom formatters and handlers to
provide rich, context-aware logging to both the console and structured files.
It ensures a consistent logging experience across the entire application.
"""
import logging
import sys
from typing import Any, MutableMapping

from aegis.utils.log_sinks import JsonlFileHandler, TaskIdFilter

_LOGGING_CONFIGURED = False


class LogColors:
    """A container for ANSI escape codes to colorize log output."""

    HEADER = "\x1b[95m"
    OKBLUE = "\x1b[94m"
    OKCYAN = "\x1b[96m"
    OKGREEN = "\x1b[92m"
    WARNING = "\x1b[93m"
    FAIL = "\x1b[91m"
    ENDC = "\x1b[0m"
    BOLD = "\x1b[1m"
    UNDERLINE = "\x1b[4m"


class ColorFormatter(logging.Formatter):
    """Custom log formatter that applies color coding and includes the task_id."""

    _format_task = (
        "%(asctime)s - [%(task_id)s] - %(levelname)-8s - %(name)-25s - %(message)s"
    )
    _format_system = (
        "%(asctime)s - [SYSTEM]   - %(levelname)-8s - %(name)-25s - %(message)s"
    )

    def format(self, record: logging.LogRecord) -> str:
        """Formats the log record with color and task ID context.

        :param record: The log record to format.
        :type record: logging.LogRecord
        :return: The formatted, colorized log string.
        :rtype: str
        """
        level_color = {
            "DEBUG": LogColors.OKBLUE,
            "INFO": LogColors.OKGREEN,
            "WARNING": LogColors.WARNING,
            "ERROR": LogColors.FAIL,
            "CRITICAL": LogColors.FAIL,
        }.get(record.levelname, LogColors.ENDC)

        # Safely get the task_id attribute set by the TaskIdFilter.
        task_id = getattr(record, "task_id", None)
        if task_id:
            log_fmt = self._format_task
        else:
            record.task_id = "SYSTEM"  # Default value for display
            log_fmt = self._format_system

        formatter = logging.Formatter(log_fmt, "%Y-%m-%d %H:%M:%S")
        formatted_msg = formatter.format(record)
        return f"{level_color}{formatted_msg}{LogColors.ENDC}"


class StructuredLoggerAdapter(logging.LoggerAdapter):
    """Extends the standard logging adapter to support structured logging.

    This adapter allows passing a dictionary of structured data via the `extra`
    parameter in a log call. It nests this data under a specific key to avoid

    conflicts with the standard logging system's own use of `extra`.
    """

    def process(
        self, msg: str, kwargs: MutableMapping[str, Any]
    ) -> tuple[str, MutableMapping[str, Any]]:
        """Processes the log message and keyword arguments.

        If `extra` is found in the kwargs, it is moved to a `extra_data` key
        to be safely handled by the `JsonlFileHandler`.

        :param msg: The original log message.
        :type msg: str
        :param kwargs: The keyword arguments passed to the log call.
        :type kwargs: MutableMapping[str, Any]
        :return: The processed message and keyword arguments.
        :rtype: tuple[str, MutableMapping[str, Any]]
        """
        if "extra" in kwargs:
            kwargs["extra_data"] = kwargs.pop("extra")
        return msg, kwargs


def setup_logger(
    name: str,
) -> StructuredLoggerAdapter:
    """Sets up the root logger and returns a structured child logger.

    This is the main entry point for obtaining a logger in any module. On the
    first call, it configures the root logger with all necessary handlers and
    filters. Subsequent calls simply retrieve a logger for the specified name.

    :param name: The name of the logger, typically `__name__`.
    :type name: str
    :return: A `StructuredLoggerAdapter` instance ready for use.
    :rtype: StructuredLoggerAdapter
    """
    global _LOGGING_CONFIGURED

    if not _LOGGING_CONFIGURED:
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)

        if root_logger.hasHandlers():
            root_logger.handlers.clear()

        # 1. Console Handler (for human-readable output)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(ColorFormatter())
        console_handler.addFilter(TaskIdFilter())
        root_logger.addHandler(console_handler)

        # 2. JSONL File Handler (for machine-readable audit trails)
        jsonl_handler = JsonlFileHandler()
        root_logger.addHandler(jsonl_handler)

        root_logger.info("Root logger configured with Console and JSONL handlers.")
        _LOGGING_CONFIGURED = True

    logger = logging.getLogger(name)
    return StructuredLoggerAdapter(logger, {})
