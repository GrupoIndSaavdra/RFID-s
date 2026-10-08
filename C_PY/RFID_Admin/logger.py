import logging
import os
from utils import get_data_path

log_file = os.path.join(get_data_path(), "app.log")

logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(module)s - %(message)s",
)


def log_error(msg: str) -> None:
    """
    Logs an error message to the log file and prints it to the console.

    Args:
        msg (str): The error message to be logged.
    """
    logging.error(msg)
    print(msg)


def log_info(msg: str) -> None:
    """
    Logs an informational message to the log file and prints it to the console.

    Args:
        msg (str): The informational message to be logged.
    """
    logging.info(msg)
    print(msg)


def log_warning(msg: str) -> None:
    """
    Logs a warning message to the log file and prints it to the console.

    Args:
        msg (str): The warning message to be logged.
    """
    logging.warning(msg)
    print(msg)
