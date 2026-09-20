"""Data contracts for memory extraction and eligibility checks."""

from typing import Literal
from uuid import UUID

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from Backend.Memory.models import ALLOWED_VALUES, MemoryKey


class MessageContext(BaseModel):
    """Server-owned metadata for one message.

    Construct only after authentication and thread ownership checks.

    message_id and sequence must remain stable across retries.
    sequence is assigned by the application within the user's
    memory event stream.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    user_id: UUID

    thread_id: str = Field(
        min_length=1,
        max_length=256,
        pattern=r"\S",
    )

    message_id: UUID

    sequence: int = Field(
        ge=1,
        strict=True,
    )

    occurred_at: AwareDatetime

    role: Literal["user", "assistant", "tool", "system"]

    text: str = Field(
        min_length=1,
        max_length=32000,
        pattern=r"\S",
    )


class EvidenceSpan(BaseModel):
    """Exact supporting text within the source message.

    start is inclusive; end is exclusive.
    Offsets use Python string positions, not byte offsets.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    start: int = Field(ge=0, strict=True)
    end: int = Field(gt=0, strict=True)

    quote: str = Field(
        min_length=1,
        max_length=2000,
        pattern=r"\S",
    )

    @model_validator(mode="after")
    def validate_bounds(self):
        if self.end <= self.start:
            raise ValueError(
                "Evidence end must be greater than start"
            )

        return self


class MemoryCandidate(BaseModel):
    """A proposed change, not an authorized database command.

    An extractor should return no candidates when there is
    nothing suitable to remember.

    Classification fields are fallible extractor predictions.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    operation: Literal["upsert", "delete"]

    memory_key: MemoryKey
    memory_value: str | None = None

    subject: Literal["self", "other", "unknown"]
    scope: Literal["durable", "trip", "unknown"]
    assertion: Literal["explicit", "inferred", "unknown"]

    evidence: EvidenceSpan

    @model_validator(mode="after")
    def validate_operation(self):
        if self.operation == "delete":
            if self.memory_value is not None:
                raise ValueError(
                    "Delete must not contain a memory value"
                )

        elif self.memory_value not in ALLOWED_VALUES[self.memory_key]:
            raise ValueError(
                "Upsert requires a supported value for its key"
            )

        return self