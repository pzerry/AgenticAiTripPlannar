import logging
import sys


LOG_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)


def setup_logging(level: str = "INFO") -> None:
    """
    Configure application-wide logging.
    Call this once when the application starts.
    """

    logging.basicConfig(
        level=level.upper(),
        format=LOG_FORMAT,
        stream=sys.stdout,
        force=True,
    )


def get_logger(name: str) -> logging.Logger:
    """
    Return a logger for a module.

    Example:
        logger = get_logger(__name__)
    """
    return logging.getLogger(name)