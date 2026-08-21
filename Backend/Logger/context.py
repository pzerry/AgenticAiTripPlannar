from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import replace
from uuid import uuid4

from Backend.Logger.models import LogContext

_context: ContextVar[LogContext] = ContextVar(
    "log_context",
    default=LogContext(),
)


def get_context() -> LogContext:
    return _context.get()


def set_context(context: LogContext) -> None:
    _context.set(context)


def clear_context() -> None:
    _context.set(LogContext())


def generate_request_id() -> str:
    return str(uuid4())


def generate_execution_id() -> str:
    return str(uuid4())


def set_request_id(request_id: str) -> Token:
    ctx = replace(get_context(), request_id=request_id)
    return _context.set(ctx)


def set_execution_id(execution_id: str) -> Token:
    ctx = replace(get_context(), execution_id=execution_id)
    return _context.set(ctx)


def set_graph_id(graph_id: str) -> Token:
    ctx = replace(get_context(), graph_id=graph_id)
    return _context.set(ctx)


def set_agent(agent_name: str | None) -> Token:
    ctx = replace(get_context(), agent_name=agent_name)
    return _context.set(ctx)


def set_tool(tool_name: str | None) -> Token:
    ctx = replace(get_context(), tool_name=tool_name)
    return _context.set(ctx)