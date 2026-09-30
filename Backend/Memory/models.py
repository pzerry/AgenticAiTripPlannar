"""Validated durable preferences. Trip-specific data is intentionally excluded."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

MemoryKey = Literal["preferred_flight_type", "preferred_hotel_class", "preferred_trip_style"]
ALLOWED_VALUES = {
    "preferred_flight_type": {"non_stop", "connecting_allowed"},
    "preferred_hotel_class": {"1_star", "2_star", "3_star", "4_star", "5_star"},
    "preferred_trip_style": {"budget_friendly", "balanced", "luxury"},
}


class SemanticMemoryInput(BaseModel):
    """An explicitly stated durable preference, accepted by application policy.

    Confidence is metadata, not a calibrated probability or write permission.
    The future extractor must distinguish durable preferences from trip requests.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, frozen=True)

    user_id: UUID
    memory_key: MemoryKey
    memory_value: str = Field(min_length=1, max_length=64)
    confidence: float = Field(default=1.0, ge=0, le=1, allow_inf_nan=False)
    source_thread_id: str = Field(min_length=1, max_length=256)

    @model_validator(mode="after")
    def validate_preference(self):
        if self.memory_value not in ALLOWED_VALUES[self.memory_key]:
            raise ValueError(f"Unsupported value for {self.memory_key}")
        return self


class SemanticMemory(SemanticMemoryInput):
    """Persisted preference and its provenance."""

    id: UUID
    created_at: datetime
    updated_at: datetime
