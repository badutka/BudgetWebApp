import logging
import coloredlogs
import os
import socket
from datetime import datetime
from typing import Any
import pandas as pd

# Optional: Generate timestamped log files instead of a fixed name
# LOG_FILE = f'{datetime.now().strftime("%m_%d_%Y_%H_%M_%S")}.log'
LOG_FILE = 'logs.log'  # Fixed log file name for consistent output

# Directory where log files will be stored
LOG_PATH = os.path.join(os.getcwd(), 'logs')
os.makedirs(LOG_PATH, exist_ok=True)  # Ensure log directory exists

# Full path to the log file
LOG_FILE_PATH = os.path.join(LOG_PATH, LOG_FILE)

# Various format experiments kept for reference:
# LOG_FORMAT = '[ %(asctime)s ] [%(lineno)d] [%(name)s] - %(levelname)s - %(message)s'
# LOG_FORMAT = '[ %(asctime)s ] [%(module)s.%(funcName)s:%(lineno)d] - %(levelname)s - %(message)s'
# LOG_FORMAT = '[ %(asctime)s ] [ %(hostname)s %(name)s[%(process)d] ] [%(module)s.%(funcName)s:%(lineno)d] - %(levelname)s - %(message)s'

# Final chosen format:
# - Timestamp
# - Hostname + Logger name + PID
# - Custom [module.func:line] section injected via a filter
LOG_FORMAT = '[ %(asctime)s ] [ %(hostname)s %(name)s[%(process)d] ] [ %(mod_func_line)s ] - %(levelname)s - %(message)s'


# LOG_FORMAT = (
#     50 * "-"  # separator line
#     + "\n[ %(asctime)s ] [ %(hostname)s %(name)s[%(process)d] ] "
#       "[%(mod_func_line)s] - %(levelname)s - %(message)s"
# )

def add_module_func_line(record: logging.LogRecord) -> bool:
    """Function-based logging filter to add module/function/line info to a log record.

    Args:
        record (logging.LogRecord): The log record being processed. Type hint helps
            PyCharm recognize this as a valid filter and suppress type warnings.

    Returns:
        bool: Always True, allowing the log record to pass through.

    Notes:
        - The injected attribute is 'mod_func_line', formatted as 'module.funcName:lineno'.
        - Using this type hint fixes PyCharm warnings about addFilter expecting a 'Filter'.
    """
    record.mod_func_line = f"{record.module}.{record.funcName}:{record.lineno}"
    return True


class ModuleFuncLineFilter(logging.Filter):
    """Class-based logging filter to add module/function/line info to a log record.

    Attributes added:
        mod_func_line (str): Formatted as 'module.funcName:lineno'.

    Usage:
        logger.addFilter(ModuleFuncLineFilter())
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Apply the filter to inject mod_func_line into the record.

        Args:
            record (logging.LogRecord): The log record being processed.

        Returns:
            bool: Always True, allowing the log record to pass through.
        """
        record.mod_func_line = f"{record.module}.{record.funcName}:{record.lineno}"
        return True


class CustomLogger(logging.getLoggerClass()):
    """Custom logger that adds hostname and log filename to each log record.

    Features:
        - Injects 'hostname' and 'logfilename' into each LogRecord.
        - Automatically applies ModuleFuncLineFilter.

    Usage:
        logging.setLoggerClass(CustomLogger)
        logger = logging.getLogger("mylogger")
    """

    def __init__(self, name: str, level: int = logging.NOTSET) -> None:
        """Initialize the custom logger.

        Args:
            name (str): Name of the logger.
            level (int): Logging level.
        """
        super().__init__(name, level)
        # self.addFilter(add_module_func_line)  # function-based
        self.addFilter(ModuleFuncLineFilter())  # class-based

    def makeRecord(self, *args: Any, **kwargs: Any) -> logging.LogRecord:
        """Override Logger.makeRecord to inject additional attributes.

        Injected attributes:
            hostname (str): Machine hostname.
            logfilename (str): Current log file name.

        Returns:
            logging.LogRecord: The enhanced log record.
        """
        record: logging.LogRecord = super().makeRecord(*args, **kwargs)
        record.hostname = socket.gethostname()  # inject hostname
        record.logfilename = LOG_FILE  # inject log file name
        return record


class DataFrameFormatter(logging.Formatter):
    """Custom formatter that pretty-prints pandas DataFrames as markdown tables.

    This formatter checks if the log record message is a pandas DataFrame.
    If it is, it converts the DataFrame into a markdown-formatted table
    (with grid borders) and prepends a newline so the table appears on a
    new line in the log output. Otherwise, the message is passed through
    unmodified.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format the specified record as text.

        If the log record's message is a pandas DataFrame, it converts it
        into a markdown table with grid borders and right-aligned values.

        Args:
            record (logging.LogRecord): The log record to format.

        Returns:
            str: The formatted log record as a string.
        """
        df: pd.DataFrame
        if isinstance(record.msg, pd.DataFrame):
            df = record.msg
            # Convert DataFrame to markdown table and start on a new line
            record.msg = "\n" + df.to_markdown(
                index=True,
                tablefmt="grid",
                stralign="right",
                numalign="right"
            )
        formatted_record: str = super().format(record)
        return formatted_record


class Singleton(type):
    """Metaclass for creating singleton classes."""

    _instances: dict[type, Any] = {}

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        """Return the singleton instance, creating it if necessary."""
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Logger(metaclass=Singleton):
    """Singleton wrapper for initializing logging."""

    def __init__(self) -> None:
        """Initialize Logger instance."""
        pass

    @staticmethod
    def initialize_logging() -> logging.Logger:
        """Initialize logging configuration with file and console handlers.

        Returns:
            logging.Logger: Configured logger instance.
        """
        if not logging.root.handlers:
            # formatter = logging.Formatter(LOG_FORMAT)
            formatter = DataFrameFormatter(LOG_FORMAT)
            logger = logging.getLogger(LOG_FILE)
            logger.setLevel(logging.DEBUG)

            # Console (Stream) handler
            ch = logging.StreamHandler()
            ch.setLevel(logging.DEBUG)
            ch.setFormatter(formatter)
            logger.addHandler(ch)

            # File handler
            fh = logging.FileHandler(LOG_FILE_PATH)
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(formatter)
            logger.addHandler(fh)

            # Colored terminal output
            coloredlogs.install(
                logger=logger,
                fmt=LOG_FORMAT,  # Use the same format as the file
                level_styles={
                    'debug': {'color': 'blue'},
                    'info': {'color': 'green'},
                    'warning': {'color': 'yellow'},
                    'error': {'color': 'red'},
                    'critical': {'color': 'red', 'bold': True}
                },
                field_styles={
                    'hostname': {'color': 'magenta'},  # Hostname in magenta
                    'name': {'color': 'red'},  # Logger name in red
                    # 'module': {'color': 'cyan', 'bold': True},  # module.func will inherit this
                    # 'funcName': {'color': 'cyan', 'bold': True},  # optional to reinforce
                    # 'lineno': {'color': 'cyan'}  # line number in same color
                    'mod_func_line': {'color': 'cyan', 'bold': True},  # custom field for module.func:line
                    'levelname': {'color': 'white', 'bold': True, 'underline': True, 'background': 'black'},
                    'asctime': {'color': 'green'}#
                }
            )

            # Ensure file handler logs DEBUG+ messages
            logger.handlers[1].setLevel(logging.DEBUG)

            logger.info(f"Logging initialized.\n{150 * '*'}")

        return logging.getLogger(LOG_FILE)


# Apply custom logger class globally
logging.setLoggerClass(CustomLogger)

# Create and configure the logger
logger = Logger().initialize_logging()
