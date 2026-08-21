from __future__ import annotations

import inspect
import time
from functools import wraps
from typing import Any, Callable

from Backend.Logger.context import (
    set_agent,
    set_tool,
)
from Backend.Logger.events import (
    execution_completed,
    execution_failed,
    execution_started,
)


def log_execution(name: str | None = None) -> Callable:
    """
    Log execution of any sync or async function.
    """

    def decorator(func: Callable):

        if inspect.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any):

                execution_name = name or func.__qualname__
                start = time.perf_counter()

                execution_started(execution_name)

                try:
                    result = await func(*args, **kwargs)

                    execution_completed(
                        name=execution_name,
                        duration_ms=(time.perf_counter() - start) * 1000,
                    )

                    return result

                except Exception:

                    execution_failed(
                        name=execution_name,
                        duration_ms=(time.perf_counter() - start) * 1000,
                    )

                    raise

            return async_wrapper

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any):

            execution_name = name or func.__qualname__
            start = time.perf_counter()

            execution_started(execution_name)

            try:
                result = func(*args, **kwargs)

                execution_completed(
                    name=execution_name,
                    duration_ms=(time.perf_counter() - start) * 1000,
                )

                return result

            except Exception:

                execution_failed(
                    name=execution_name,
                    duration_ms=(time.perf_counter() - start) * 1000,
                )

                raise

        return sync_wrapper

    return decorator


def log_agent(agent_name: str) -> Callable:
    """
    Log AI agent execution.
    """

    def decorator(func: Callable):

        execution_logger = log_execution(agent_name)(func)

        if inspect.iscoroutinefunction(func):

            @wraps(func)
            async def wrapper(*args, **kwargs):

                token = set_agent(agent_name)

                try:
                    return await execution_logger(*args, **kwargs)

                finally:
                    token.var.reset(token)

        else:

            @wraps(func)
            def wrapper(*args, **kwargs):

                token = set_agent(agent_name)

                try:
                    return execution_logger(*args, **kwargs)

                finally:
                    token.var.reset(token)

        return wrapper

    return decorator


def log_tool(tool_name: str) -> Callable:
    """
    Log tool execution.
    """

    def decorator(func: Callable):

        execution_logger = log_execution(tool_name)(func)

        if inspect.iscoroutinefunction(func):

            @wraps(func)
            async def wrapper(*args, **kwargs):

                token = set_tool(tool_name)

                try:
                    return await execution_logger(*args, **kwargs)

                finally:
                    token.var.reset(token)

        else:

            @wraps(func)
            def wrapper(*args, **kwargs):

                token = set_tool(tool_name)

                try:
                    return execution_logger(*args, **kwargs)

                finally:
                    token.var.reset(token)

        return wrapper

    return decorator


def log_api(service: str) -> Callable:
    """
    Log external API execution.
    """
    return log_execution(service)


def log_llm(provider: str) -> Callable:
    """
    Log LLM execution.
    """
    return log_execution(provider)