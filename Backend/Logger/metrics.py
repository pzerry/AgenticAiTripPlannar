from __future__ import annotations

from Backend.Logger.models import (
    APIMetrics,
    ExecutionMetrics,
    LLMMetrics,
    ToolMetrics,
)


def execution_metrics(
    duration_ms: float,
    success: bool = True,
    retry_count: int = 0,
) -> ExecutionMetrics:
    """Create execution metrics."""

    return ExecutionMetrics(
        duration_ms=duration_ms,
        success=success,
        retry_count=retry_count,
    )


def api_metrics(
    *,
    service: str,
    endpoint: str | None = None,
    method: str | None = None,
    status_code: int | None = None,
    latency_ms: float | None = None,
) -> APIMetrics:
    """Create API metrics."""

    return APIMetrics(
        service=service,
        endpoint=endpoint,
        method=method,
        status_code=status_code,
        latency_ms=latency_ms,
    )


def tool_metrics(
    *,
    tool_name: str,
    duration_ms: float,
    success: bool = True,
) -> ToolMetrics:
    """Create tool metrics."""

    return ToolMetrics(
        tool_name=tool_name,
        duration_ms=duration_ms,
        success=success,
    )


def llm_metrics(
    *,
    provider: str,
    model: str,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    estimated_cost: float = 0,
) -> LLMMetrics:
    """Create LLM metrics."""

    total_tokens = (
        prompt_tokens +
        completion_tokens
    )

    return LLMMetrics(
        provider=provider,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        estimated_cost=estimated_cost,
    )