from __future__ import annotations

from Backend.Logger import get_logger
from Backend.Logger.metrics import (
    api_metrics,
    execution_metrics,
    llm_metrics,
)

logger = get_logger(__name__)


# ==========================================================
# Execution
# ==========================================================

def execution_started(name: str) -> None:
    logger.info("Started %s", name)


def execution_completed(
    *,
    name: str,
    duration_ms: float,
) -> None:
    metrics = execution_metrics(
        duration_ms=duration_ms,
    )

    logger.info(
        "Completed %s | %.2f ms",
        name,
        metrics.duration_ms,
    )


def execution_failed(
    *,
    name: str,
    duration_ms: float,
    retry_count: int = 0,
) -> None:

    metrics = execution_metrics(
        duration_ms=duration_ms,
        success=False,
        retry_count=retry_count,
    )

    logger.exception(
        "Failed %s | %.2f ms | retries=%d",
        name,
        metrics.duration_ms,
        metrics.retry_count,
    )


# ==========================================================
# API
# ==========================================================

def api_started(
    *,
    service: str,
    endpoint: str,
    method: str,
) -> None:

    metrics = api_metrics(
        service=service,
        endpoint=endpoint,
        method=method,
    )

    logger.info(
        "[%s] %s %s",
        metrics.service,
        metrics.method,
        metrics.endpoint,
    )


def api_completed(
    *,
    service: str,
    status_code: int,
    latency_ms: float,
) -> None:

    metrics = api_metrics(
        service=service,
        status_code=status_code,
        latency_ms=latency_ms,
    )

    logger.info(
        "[%s] status=%d latency=%.2f ms",
        metrics.service,
        metrics.status_code,
        metrics.latency_ms,
    )


def api_failed(
    *,
    service: str,
    message: str,
) -> None:

    logger.exception(
        "[%s] %s",
        service,
        message,
    )


# ==========================================================
# LLM
# ==========================================================

def llm_completed(
    *,
    provider: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    estimated_cost: float,
) -> None:

    metrics = llm_metrics(
        provider=provider,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        estimated_cost=estimated_cost,
    )

    logger.info(
        "[LLM] provider=%s model=%s prompt=%d completion=%d total=%d cost=$%.6f",
        metrics.provider,
        metrics.model,
        metrics.prompt_tokens,
        metrics.completion_tokens,
        metrics.total_tokens,
        metrics.estimated_cost,
    )