from __future__ import annotations

import logging

from Backend.Logger.context import get_context


class CustomFormatter(logging.Formatter):
    """
    Production log formatter.
    Automatically injects runtime context into every log record.
    """

    FORMAT = (
        "%(asctime)s | "
        "%(levelname)-8s | "
        "Request=%(request_id)s | "
        "Execution=%(execution_id)s | "
        "Agent=%(agent_name)s | "
        "Tool=%(tool_name)s | "
        "%(name)s | "
        "%(funcName)s:%(lineno)d | "
        "%(message)s"
    )

    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

    def __init__(self) -> None:
        super().__init__(
            fmt=self.FORMAT,
            datefmt=self.DATE_FORMAT,
        )

    def format(self, record: logging.LogRecord) -> str:
        """
        Inject request context into every log record.
        """

        context = get_context()

        record.request_id = context.request_id or "-"
        record.execution_id = context.execution_id or "-"
        record.agent_name = context.agent_name or "-"
        record.tool_name = context.tool_name or "-"

        return super().format(record)