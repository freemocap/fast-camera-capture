from .custom_formatter import CustomFormatter
import logging

from ..log_format_string import LOG_POINTER_STRING
from ..logging_color_helpers import get_hashed_color


class ColorFormatter(CustomFormatter):
    """Adds ANSI colors to PID, TID, and log messages"""

    COLOR_CODES = {
        "LOOP": "\033[90m",  # Grey
        "TRACE": "\033[37m",  # White
        "DEBUG": "\033[34m",  # Blue
        "INFO": "\033[96m",  # Cyan
        "SUCCESS": "\033[95m",  # Magenta
        "API": "\033[92m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[41m",  # Red background
    }

    def format(self, record: logging.LogRecord) -> str:
        # Apply PID/TID colors
        record.pid_color = get_hashed_color(record.process)
        record.tid_color = get_hashed_color(record.thread)

        # Apply level color to message
        level_color = self.COLOR_CODES.get(record.levelname, "")
        record.msg = f"{level_color}{record.msg}\033[0m"

        # Format with parent class
        formatted = super().format(record)

        # Add color to structural elements
        return formatted.replace(LOG_POINTER_STRING, f"{level_color}{LOG_POINTER_STRING}\033[0m")