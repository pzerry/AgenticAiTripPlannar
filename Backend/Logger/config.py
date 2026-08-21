from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from Backend.Config.loader import load_config

from Backend.Logger.formatter import CustomFormatter

config = load_config()


def _console_handler() -> logging.Handler:
    """Create console handler."""

    logging_config = config["logging"]

    handler = logging.StreamHandler()

    handler.setLevel(logging_config["level"].upper())
    handler.setFormatter(CustomFormatter())

    return handler


def _file_handler() -> logging.Handler:
    """Create application log handler."""

    logging_config = config["logging"]

    log_dir = Path(logging_config["directory"])
    log_dir.mkdir(parents=True, exist_ok=True)

    handler = RotatingFileHandler(
        filename=log_dir / "travel.log",
        maxBytes=logging_config["max_bytes"],
        backupCount=logging_config["backup_count"],
        encoding="utf-8",
    )

    handler.setLevel(logging_config["level"].upper())
    handler.setFormatter(CustomFormatter())

    return handler


def _error_handler() -> logging.Handler:
    """Create error log handler."""

    logging_config = config["logging"]

    log_dir = Path(logging_config["directory"])
    log_dir.mkdir(parents=True, exist_ok=True)

    handler = RotatingFileHandler(
        filename=log_dir / "error.log",
        maxBytes=logging_config["max_bytes"],
        backupCount=logging_config["backup_count"],
        encoding="utf-8",
    )

    handler.setLevel(logging.ERROR)
    handler.setFormatter(CustomFormatter())

    return handler


def get_handlers() -> list[logging.Handler]:
    """
    Return enabled logging handlers.

    Supports console-only, file-only,
    or both using config.yaml.
    """

    logging_config = config["logging"]

    handlers: list[logging.Handler] = []

    if logging_config.get("console", True):
        handlers.append(_console_handler())

    if logging_config.get("file", True):
        handlers.append(_file_handler())
        handlers.append(_error_handler())

    return handlers