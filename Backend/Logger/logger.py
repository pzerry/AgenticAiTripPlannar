from __future__ import annotations

import logging

from Backend.Config.loader import load_config

from Backend.Logger.config import get_handlers

config = load_config()


def setup_logging() -> None:
    """
    Configure the application logger.

    Safe to call multiple times.
    """

    logger = logging.getLogger("trip_planner")

    if logger.handlers:
        return

    logger.setLevel(config["logging"]["level"].upper())

    logger.propagate = False

    for handler in get_handlers():
        logger.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """
    Return a child logger.

    Example:
        logger = get_logger(__name__)
    """

    return logging.getLogger(f"trip_planner.{name}")