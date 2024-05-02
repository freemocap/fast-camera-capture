import logging
import sys
from logging.config import dictConfig

from skellycam.system.default_paths import get_log_file_path
from skellycam.system.logging_configuration.custom_formatter import (
    CustomFormatter,
)
from skellycam.system.logging_configuration.delta_time_filter import (
    DeltaTimeFilter,
)
from skellycam.system.logging_configuration.log_level_enum import (
    LogLevel,
)
from skellycam.system.logging_configuration.logging_color_helpers import (
    get_hashed_color,
)


class LoggerBuilder:
    DEFAULT_LOGGING = {"version": 1, "disable_existing_loggers": False}

    format_string = (
        "---------------------------------------| %(levelname)s | %(name)s:%(funcName)s():%(lineno)s | %(asctime)s | %(delta_t)s | PID:%(process)d:%(processName)s TID:%(thread)d:%(threadName)s \n%(message)s"
    )

    def __init__(self, level: LogLevel):
        self.default_logging_formatter = CustomFormatter(
            fmt=self.format_string, datefmt="%Y-%m-%dT%H:%M:%S"
        )
        dictConfig(self.DEFAULT_LOGGING)

        self._set_logging_level(level)

    def _set_logging_level(self, level: LogLevel):
        logging.root.setLevel(level.value)

    def build_file_handler(self):
        file_handler = logging.FileHandler(get_log_file_path(), encoding="utf-8")
        file_handler.setLevel(LogLevel.TRACE.value)
        file_handler.setFormatter(self.default_logging_formatter)
        file_handler.addFilter(DeltaTimeFilter())
        return file_handler

    class ColoredConsoleHandler(logging.StreamHandler):
        COLORS = {
            # Define color codes for different log levels with ANSI escape codes
            "TRACE": "\033[37m",  # Dark White (grey)
            "DEBUG": "\033[34m",  # Blue
            "INFO": "\033[96m",  # Cyan
            "SUCCESS": "\033[95m",  # Magenta
            "WARNING": "\033[33m",  # Yellow
            "ERROR": "\033[30m\033[41m",  # Black text on Red background
        }

        def emit(self, record):
            """
            Overrides the emit method to colorize logs according to the level when
            outputting to the console.
            """
            # Apply color to indicate the process ID (PID) first
            pid_color = get_hashed_color(record.process)
            record.process_colored = pid_color + f"PID:{record.process}:{record.processName}" + "\033[0m"

            # Then apply color to indicate the thread ID (TID)
            tid_color = get_hashed_color(record.thread)
            record.thread_colored = tid_color + f"TID:{record.thread}:{record.threadName}" + "\033[0m"



            # Use the CustomFormatter to format the record
            formatted_record = self.format(record)

            # Apply color code to the formatted record except PID and TID
            color_code = self.COLORS.get(record.levelname, "\033[0m")
            formatted_record = (
                formatted_record
                .replace(f"PID:{record.process}:{record.processName}", record.process_colored)
                .replace(f"TID:{record.thread}:{record.threadName}", record.thread_colored)
            )

            formatted_record = formatted_record.replace(record.getMessage(),
                                                        color_code + record.getMessage() + "\033[0m")
            formatted_record = color_code + formatted_record + "\033[0m"
            # Output the final colorized and formatted record to the console
            print(formatted_record)

    def build_console_handler(self):
        console_handler = self.ColoredConsoleHandler(stream=sys.stdout)
        console_handler.setLevel(LogLevel.TRACE.value)
        console_handler.setFormatter(self.default_logging_formatter)
        console_handler.addFilter(DeltaTimeFilter())
        return console_handler

    def configure(self):
        if len(logging.getLogger().handlers) == 0:
            handlers = [self.build_file_handler(), self.build_console_handler()]
            for handler in handlers:
                if handler not in logging.getLogger("").handlers:
                    logging.getLogger("").handlers.append(handler)
        else:
            logger = logging.getLogger(__name__)

            logger.info("Logging already configured")
