import logging
import sys
from logging import Logger, LoggerAdapter
from typing import Any


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
    """
    Represents the ColorFormatter class.

    Custom log formatter that applies color coding to log messages based on severity.
    """

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
        formatted = super().format(record)
        return f"{level_color}{formatted}{LogColors.ENDC}"


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
        extra = kwargs.get("extra", {})
        extra["event_type"] = kwargs.pop("event_type", None)
        extra["data"] = kwargs.pop("data", None)
        kwargs["extra"] = extra
        return msg, kwargs


def setup_logger(name: str) -> StructuredLoggerAdapter[Logger | LoggerAdapter[Any] | Any]:
    """
    setup_logger
    :param name: Description of name
    :type name: Any
    :return: Description of return value
    :rtype: Any
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = ColorFormatter("%(asctime)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return StructuredLoggerAdapter(logger, {})
