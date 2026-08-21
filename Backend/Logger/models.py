from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class ExecutionMetrics:
    """Execution timing information."""

    duration_ms: float | None = None
    success: bool = True
    retry_count: int = 0


@dataclass(slots=True)
class APIMetrics:
    """External API metrics."""

    service: str
    endpoint: str | None = None
    method: str | None = None
    status_code: int | None = None
    latency_ms: float | None = None


@dataclass(slots=True)
class LLMMetrics:
    """LLM usage metrics."""

    provider: str
    model: str

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    estimated_cost: float = 0.0


@dataclass(slots=True)
class ToolMetrics:
    """Tool execution metrics."""

    tool_name: str
    duration_ms: float | None = None
    success: bool = True


@dataclass(slots=True)
class LogContext:
    """Context shared by every log."""

    request_id: str | None = None
    execution_id: str | None = None
    graph_id: str | None = None
    agent_name: str | None = None
    tool_name: str | None = None


@dataclass(slots=True)
class LogEvent:
    """Complete structured log event."""

    timestamp: datetime = field(default_factory=datetime.utcnow)

    level: str = "INFO"

    message: str = ""

    context: LogContext = field(default_factory=LogContext)

    execution: ExecutionMetrics | None = None

    api: APIMetrics | None = None

    llm: LLMMetrics | None = None

    tool: ToolMetrics | None = None

    metadata: dict[str, Any] = field(default_factory=dict)