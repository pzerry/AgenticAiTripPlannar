"""Policy-gated atomic writes with ordering and deletion fences."""

from dataclasses import dataclass

from psycopg import AsyncConnection
from psycopg.rows import dict_row

from Backend.Memory.contracts import MemoryCandidate, MessageContext
from Backend.Memory.events import ClaimedEvent
from Backend.Memory.models import SemanticMemoryInput
from Backend.Memory.policy import evaluate_candidate
from Backend.Memory.semantic_memory import SemanticMemoryRepository


class LostLeaseError(RuntimeError):
    """A worker must discard its result after losing its event lease."""


@dataclass(frozen=True)
class WriteResult:
    accepted: int = 0
    rejected: int = 0
    stale: int = 0


async def apply_candidates(conn: AsyncConnection, claim: ClaimedEvent,
                           candidates: list[MemoryCandidate]) -> WriteResult:
    """All candidates and event completion commit together, or none do.

    A tombstone retains only ordering metadata after deletion. Older accepted
    events cannot bring back a forgotten value. Server capture order, not model
    completion time or client timestamps, defines 'newer'.
    """
    if len(candidates) > 3:
        raise ValueError("At most one candidate per supported key is allowed")
    candidates = [MemoryCandidate.model_validate(c.model_dump()) for c in candidates]
    if len({c.memory_key for c in candidates}) != len(candidates):
        raise ValueError("Ambiguous duplicate memory keys")
    counts = {"accepted": 0, "rejected": 0, "stale": 0}
    repository = SemanticMemoryRepository()
    async with conn.transaction(), conn.cursor(row_factory=dict_row) as cur:
        await cur.execute("""SELECT * FROM memory_events WHERE user_id = %s AND message_id = %s
            AND status = 'processing' AND lease_token = %s AND lease_until > NOW()
            AND expires_at > NOW() FOR UPDATE""",
            (claim.context.user_id, claim.context.message_id, claim.lease_token))
        row = await cur.fetchone()
        if row is None:
            raise LostLeaseError("Memory event lease is no longer active")
        # Never authorize writes using caller-provided text, ordering, or role.
        context = MessageContext(user_id=row["user_id"], message_id=row["message_id"],
            thread_id=row["thread_id"], sequence=row["sequence"], occurred_at=row["occurred_at"],
            text=row["source_text"], role="user")
        # Deterministic key order prevents deadlocks between multi-key events.
        for candidate in sorted(candidates, key=lambda c: c.memory_key):
            decision = evaluate_candidate(context, candidate)
            if not decision.eligible:
                counts["rejected"] += 1
                continue
            await cur.execute("""INSERT INTO memory_versions
                (user_id, memory_key, source_sequence, source_message_id, deleted)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (user_id, memory_key) DO UPDATE SET
                    source_sequence = EXCLUDED.source_sequence,
                    source_message_id = EXCLUDED.source_message_id,
                    revision = memory_versions.revision + 1,
                    deleted = EXCLUDED.deleted, updated_at = clock_timestamp()
                WHERE memory_versions.source_sequence < EXCLUDED.source_sequence
                RETURNING revision""",
                (context.user_id, candidate.memory_key, context.sequence,
                 context.message_id, candidate.operation == "delete"))
            if await cur.fetchone() is None:
                counts["stale"] += 1
                continue
            if candidate.operation == "delete":
                await repository.delete(conn, user_id=context.user_id, memory_key=candidate.memory_key)
            else:
                await repository.save(conn, SemanticMemoryInput(user_id=context.user_id,
                    memory_key=candidate.memory_key, memory_value=candidate.memory_value,
                    source_thread_id=context.thread_id))
            counts["accepted"] += 1
        await cur.execute("""UPDATE memory_events SET status = 'complete', source_text = NULL,
            lease_token = NULL, lease_until = NULL, error_code = NULL
            WHERE user_id = %s AND message_id = %s""", (context.user_id, context.message_id))
    return WriteResult(**counts)
