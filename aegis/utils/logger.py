# aegis/utils/logger.py
"""
Centralized logging setup for the AEGIS framework.

This module configures the root logger with custom formatters and handlers to
provide rich, context-aware logging to both the console and structured files.
It ensures a consistent logging experience across the entire application.
"""
import logging
import os
import sys
from typing import Any, MutableMapping

from pythonjsonlogger import jsonlogger

from aegis.utils.config import get_config
from aegis.utils.log_sinks import TaskIdFilter

_LOGGING_CONFIGURED = False


class StructuredLoggerAdapter(logging.LoggerAdapter):
    """Extends the standard logging adapter to support structured logging.

    This adapter allows passing a dictionary of structured data via the `extra`
    parameter in a log call. It ensures this data is correctly prepared
    for the `JsonlFileHandler`.
    """

    def process(
        self, msg: str, kwargs: MutableMapping[str, Any]
    ) -> tuple[str, MutableMapping[str, Any]]:
        """Processes the log message and keyword arguments.

        If an 'extra' dictionary is passed in the logging call, this method
        wraps it under an 'extra_data' key within the 'extra' argument that
        the underlying logger will process. This allows the `JsonlFileHandler`
        to find the custom structured data at `record.extra_data`.

        :param msg: The original log message.
        :type msg: str
        :param kwargs: The keyword arguments passed to the log call.
        :type kwargs: MutableMapping[str, Any]
        :return: The processed message and keyword arguments.
        :rtype: tuple[str, MutableMapping[str, Any]]
        """
        original_extra_content = kwargs.get("extra")
        if original_extra_content is not None:
            kwargs["extra"] = {"extra_data": original_extra_content}
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
        
        # Get log level from config.yaml, fallback to info
        try:
            config = get_config()
            log_level_str = config.get("logging", {}).get("level", "info").upper()
        except FileNotFoundError:
            log_level_str = os.getenv("AEGIS_LOG_LEVEL", "info").upper()

        level = getattr(logging, log_level_str, logging.INFO)
        root_logger.setLevel(level)

        if root_logger.hasHandlers():
            root_logger.handlers.clear()

        # Configure console handler to output structured JSON logs to stdout
        console_handler = logging.StreamHandler(sys.stdout)
        # The format string includes standard fields plus our custom task_id
        formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(name)s %(levelname)s %(task_id)s %(message)s"
        )
        console_handler.setFormatter(formatter)
        console_handler.addFilter(TaskIdFilter())
        root_logger.addHandler(console_handler)

        root_logger.info(
            f"Root logger configured with JSON stdout handler. Level: {log_level_str}"
        )
        _LOGGING_CONFIGURED = True

    logger_instance = logging.getLogger(name)
    return StructuredLoggerAdapter(logger_instance, {})