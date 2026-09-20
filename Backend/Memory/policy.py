"""Deterministic eligibility checks for proposed memories."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from Backend.Memory.contracts import (
    MemoryCandidate,
    MessageContext,
)


DecisionReason = Literal[
    "eligible",
    "non_user_source",
    "evidence_mismatch",
    "not_self",
    "not_explicit",
    "not_durable",
]


class PolicyDecision(BaseModel):
    """Eligibility for further processing; no write has occurred."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    eligible: bool
    reason: DecisionReason


def evaluate_candidate(
    context: MessageContext,
    candidate: MemoryCandidate,
) -> PolicyDecision:
    """Check source evidence and candidate classifications.

    This does not perform authentication, semantic verification,
    conflict resolution, deduplication, or database operations.
    """

    # Revalidate objects, including those created through
    # model_construct() or modified through model_copy().
    context = MessageContext.model_validate(
        context.model_dump()
    )

    candidate = MemoryCandidate.model_validate(
        candidate.model_dump()
    )

    evidence = candidate.evidence
    reason: DecisionReason = "eligible"

    if context.role != "user":
        reason = "non_user_source"

    elif (
        evidence.end > len(context.text)
        or context.text[evidence.start:evidence.end]
        != evidence.quote
    ):
        reason = "evidence_mismatch"

    elif candidate.subject != "self":
        reason = "not_self"

    elif candidate.assertion != "explicit":
        reason = "not_explicit"

    elif candidate.scope != "durable":
        reason = "not_durable"

    return PolicyDecision(
        eligible=reason == "eligible",
        reason=reason,
    )