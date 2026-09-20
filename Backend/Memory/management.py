"""Explicit user deletion uses the same sequence fence as extracted updates."""

from uuid import UUID, uuid4

from psycopg.rows import dict_row

from Backend.Memory.contracts import EvidenceSpan, MemoryCandidate, MessageContext
from Backend.Memory.events import ClaimedEvent, EventRepository, MessageInput
from Backend.Memory.models import MemoryKey
from Backend.Memory.persistence import apply_candidates


async def forget_preference(conn, *, user_id: UUID, memory_key: MemoryKey, request_id: UUID) -> None:
    """Delete immediately and prevent older in-flight extraction from restoring it.

    This endpoint is an explicit user command, so it needs no LLM classification.
    Capture, claim and deletion commit together: a background worker cannot see
    the event between capture and this command claiming it.
    """
    text = f"Forget my saved {memory_key} preference."
    message = MessageInput(user_id=user_id, message_id=request_id,
                           thread_id=f"memory-management:{user_id}", text=text)
    async with conn.transaction():
        event = await EventRepository().capture(conn, message)
        if event.status == "complete":
            return  # Retry the original deletion, not a new higher-sequence delete.
        token = uuid4()
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute("""UPDATE memory_events SET status = 'processing', attempts = attempts + 1,
                lease_token = %s, lease_until = NOW() + INTERVAL '90 seconds'
                WHERE user_id = %s AND message_id = %s AND status = 'pending' AND attempts = 0
                RETURNING *""", (token, user_id, request_id))
            row = await cur.fetchone()
        if row is None:
            raise ValueError("Deletion event cannot be claimed")
        claim = ClaimedEvent(context=MessageContext(user_id=user_id, message_id=request_id,
            thread_id=message.thread_id, sequence=row["sequence"], occurred_at=row["occurred_at"],
            role="user", text=text), lease_token=token, lease_until=row["lease_until"], attempts=row["attempts"])
        await apply_candidates(conn, claim, [MemoryCandidate(
            operation="delete", memory_key=memory_key, memory_value=None,
            subject="self", scope="durable", assertion="explicit",
            evidence=EvidenceSpan(start=0, end=len(text), quote=text),
        )])
