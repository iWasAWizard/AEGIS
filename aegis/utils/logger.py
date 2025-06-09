# aegis/utils/logger.py
import logging
import sys
from logging import Logger, LoggerAdapter
from typing import Any

from aegis.utils.log_sinks import JsonlFileHandler, TaskIdFilter

_LOGGING_CONFIGURED = False


class LogColors:
    """
    Represents the LogColors class.

    Use this class to define ANSI escape codes for colored log output across different log levels.
    """

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

    _format = (
        "%(asctime)s - [%(task_id)s] - %(levelname)-8s - %(name)-25s - %(message)s"
    )
    _format_notask = (
        "%(asctime)s - [SYSTEM]   - %(levelname)-8s - %(name)-25s - %(message)s"
    )

    def format(self, record):
        """
        format
        :param record: Description of record
        :type record: Any
        :return: Description of return value
        :rtype: Any
        """
        level_color = {
            "DEBUG": LogColors.OKBLUE,
            "INFO": LogColors.OKGREEN,
            "WARNING": LogColors.WARNING,
            "ERROR": LogColors.FAIL,
            "CRITICAL": LogColors.FAIL,
        }.get(record.levelname, LogColors.ENDC)

        if hasattr(record, "task_id") and record.task_id:
            log_fmt = self._format
        else:
            record.task_id = "SYSTEM"  # Default value for display
            log_fmt = self._format_notask

        formatter = logging.Formatter(log_fmt, "%Y-%m-%d %H:%M:%S")
        formatted_msg = formatter.format(record)
        return f"{level_color}{formatted_msg}{LogColors.ENDC}"


class StructuredLoggerAdapter(logging.LoggerAdapter):
    """
    Represents the StructuredLoggerAdapter class.

    Extends the standard logging adapter to support structured logging with event type metadata.
    """

    def process(self, msg, kwargs):
        """
        process
        :param msg: Description of msg
        :param kwargs: Description of kwargs
        :type msg: Any
        :type kwargs: Any
        :return: Description of return value
        :rtype: Any
        """
        # Move the 'extra' dict into a specific key so it doesn't conflict
        # with the standard 'extra' used by the logging system itself.
        if "extra" in kwargs:
            kwargs["extra"] = {"extra_data": kwargs["extra"]}
        return msg, kwargs


def setup_logger(
    name: str,
) -> StructuredLoggerAdapter[Logger | LoggerAdapter[Any] | Any]:
    """
    Sets up the root logger with all handlers and returns a child logger.
    :param name: Description of name
    :type name: Any
    :return: Description of return value
    :rtype: Any
    """
    global _LOGGING_CONFIGURED

    if not _LOGGING_CONFIGURED:
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)  # Set the base level for the whole system

        # Clear any existing handlers to prevent duplicates in interactive environments
        if root_logger.hasHandlers():
            root_logger.handlers.clear()

        # 1. Console Handler (for developer-facing output)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(ColorFormatter())
        console_handler.addFilter(TaskIdFilter())  # Add filter to get task_id
        root_logger.addHandler(console_handler)

        # 2. JSONL File Handler (for machine-readable audit trails)
        jsonl_handler = JsonlFileHandler()
        root_logger.addHandler(jsonl_handler)

        root_logger.info("Root logger configured with Console and JSONL handlers.")
        _LOGGING_CONFIGURED = True

    # Return a logger for the specific module, now with a structured adapter.
    logger = logging.getLogger(name)
    return StructuredLoggerAdapter(logger, {})
