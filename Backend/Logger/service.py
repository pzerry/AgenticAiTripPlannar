from __future__ import annotations

from Backend.Logger.events import (
    api_completed,
    api_failed,
    api_started,
    execution_completed,
    execution_failed,
    execution_started,
    llm_completed,
)


class LoggingService:
    """
    Facade for all logging operations.
    """

    # =====================================================
    # Execution
    # =====================================================

    @staticmethod
    def execution_started(name: str) -> None:
        execution_started(name)

    @staticmethod
    def execution_completed(
        name: str,
        duration_ms: float,
    ) -> None:
        execution_completed(
            name=name,
            duration_ms=duration_ms,
        )

    @staticmethod
    def execution_failed(
        name: str,
        duration_ms: float,
        retry_count: int = 0,
    ) -> None:
        execution_failed(
            name=name,
            duration_ms=duration_ms,
            retry_count=retry_count,
        )

    # =====================================================
    # API
    # =====================================================

    @staticmethod
    def api_started(
        service: str,
        endpoint: str,
        method: str,
    ) -> None:
        api_started(
            service=service,
            endpoint=endpoint,
            method=method,
        )

    @staticmethod
    def api_completed(
        service: str,
        status_code: int,
        latency_ms: float,
    ) -> None:
        api_completed(
            service=service,
            status_code=status_code,
            latency_ms=latency_ms,
        )

    @staticmethod
    def api_failed(
        service: str,
        message: str,
    ) -> None:
        api_failed(
            service=service,
            message=message,
        )

    # =====================================================
    # LLM
    # =====================================================

    @staticmethod
    def llm_completed(
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        estimated_cost: float,
    ) -> None:
        llm_completed(
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            estimated_cost=estimated_cost,
        )