"""Durable message capture and leased work. No LLM calls or implicit commits.

Only the authenticated application boundary may supply user_id. A client UUID
alone is not authentication. Use a transaction around each public operation.
"""

import hashlib
from datetime import datetime
from uuid import UUID, uuid4

from psycopg import AsyncConnection
from psycopg.rows import dict_row
from pydantic import BaseModel, ConfigDict, Field

from Backend.Memory.contracts import MessageContext


class OwnershipError(PermissionError):
    """The requested thread belongs to a different principal."""


class DuplicateMessageError(ValueError):
    """An idempotency key was reused with different content."""


class MessageInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    user_id: UUID
    message_id: UUID
    thread_id: str = Field(min_length=1, max_length=256, pattern=r"\S")
    text: str = Field(min_length=1, max_length=32000, pattern=r"\S")


class CapturedEvent(BaseModel):
    user_id: UUID
    message_id: UUID
    sequence: int
    status: str


class ClaimedEvent(BaseModel):
    context: MessageContext
    lease_token: UUID
    lease_until: datetime
    attempts: int


class EventRepository:
    async def capture(self, conn: AsyncConnection, message: MessageInput) -> CapturedEvent:
        message = MessageInput.model_validate(message.model_dump())
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute("INSERT INTO memory_users (user_id) VALUES (%s) ON CONFLICT DO NOTHING",
                              (message.user_id,))
            # Serialize only this user's captures; never hold this across LLM calls.
            await cur.execute("SELECT last_sequence FROM memory_users WHERE user_id = %s FOR UPDATE",
                              (message.user_id,))
            await cur.execute("""INSERT INTO memory_threads (thread_id, user_id)
                VALUES (%s, %s) ON CONFLICT DO NOTHING""", (message.thread_id, message.user_id))
            await cur.execute("SELECT user_id FROM memory_threads WHERE thread_id = %s", (message.thread_id,))
            if (await cur.fetchone())["user_id"] != message.user_id:
                raise OwnershipError("Thread is not owned by this user")
            digest = hashlib.sha256(message.text.encode()).hexdigest()
            await cur.execute("SELECT * FROM memory_events WHERE user_id = %s AND message_id = %s",
                              (message.user_id, message.message_id))
            existing = await cur.fetchone()
            if existing:
                if existing["payload_hash"] != digest or existing["thread_id"] != message.thread_id:
                    raise DuplicateMessageError("Message ID was reused with different content")
                return CapturedEvent(**{key: existing[key] for key in CapturedEvent.model_fields})
            await cur.execute("""UPDATE memory_users SET last_sequence = last_sequence + 1
                WHERE user_id = %s RETURNING last_sequence""", (message.user_id,))
            sequence = (await cur.fetchone())["last_sequence"]
            await cur.execute("""INSERT INTO memory_events
                (user_id, message_id, thread_id, sequence, payload_hash, source_text)
                VALUES (%s, %s, %s, %s, %s, %s)""",
                (message.user_id, message.message_id, message.thread_id, sequence, digest, message.text))
        return CapturedEvent(user_id=message.user_id, message_id=message.message_id,
                             sequence=sequence, status="pending")

    async def assert_owner(self, conn: AsyncConnection, *, user_id: UUID, thread_id: str) -> None:
        cursor = await conn.execute("SELECT user_id FROM memory_threads WHERE thread_id = %s", (thread_id,))
        row = await cursor.fetchone()
        if row is None or row[0] != user_id:
            raise OwnershipError("Thread is not owned by this user")

    async def claim(self, conn: AsyncConnection, *, lease_seconds: int = 90,
                    max_attempts: int = 3) -> ClaimedEvent | None:
        if not 1 <= lease_seconds <= 600 or not 1 <= max_attempts <= 10:
            raise ValueError("Invalid worker limits")
        token = uuid4()
        async with conn.cursor(row_factory=dict_row) as cur:
            # Exhausted crashed jobs and expired payloads cannot stay stuck forever.
            await cur.execute("""UPDATE memory_events SET
                status = CASE WHEN expires_at <= NOW() THEN 'expired' ELSE 'failed' END,
                source_text = NULL, lease_token = NULL, lease_until = NULL
                WHERE status IN ('pending', 'processing')
                AND (expires_at <= NOW() OR
                     (attempts >= %s AND COALESCE(lease_until, NOW()) <= NOW()))""", (max_attempts,))
            await cur.execute("""WITH next_event AS (
                SELECT user_id, message_id FROM memory_events
                WHERE status IN ('pending', 'processing') AND available_at <= NOW()
                    AND (lease_until IS NULL OR lease_until <= NOW())
                    AND expires_at > NOW() AND attempts < %s
                ORDER BY occurred_at, sequence
                FOR UPDATE SKIP LOCKED LIMIT 1
            ) UPDATE memory_events e SET status = 'processing', attempts = attempts + 1,
                lease_token = %s, lease_until = NOW() + %s * INTERVAL '1 second'
                FROM next_event n WHERE e.user_id = n.user_id AND e.message_id = n.message_id
                RETURNING e.*""", (max_attempts, token, lease_seconds))
            row = await cur.fetchone()
        if row is None:
            return None
        return ClaimedEvent(context=MessageContext(
            user_id=row["user_id"], thread_id=row["thread_id"], message_id=row["message_id"],
            sequence=row["sequence"], occurred_at=row["occurred_at"], role="user", text=row["source_text"]),
            lease_token=token, lease_until=row["lease_until"], attempts=row["attempts"])

    async def fail(self, conn: AsyncConnection, claim: ClaimedEvent, *,
                   error_code: str, max_attempts: int = 3) -> None:
        # Store only bounded categories, never an exception body or source message.
        if error_code not in {"extraction_error", "invalid_output", "timeout"}:
            raise ValueError("Unsupported error category")
        await conn.execute("""UPDATE memory_events SET
            status = CASE WHEN attempts >= %s THEN 'failed' ELSE 'pending' END,
            source_text = CASE WHEN attempts >= %s THEN NULL ELSE source_text END,
            error_code = %s, lease_token = NULL, lease_until = NULL,
            available_at = NOW() + LEAST(300, POWER(2, attempts)) * INTERVAL '1 second'
            WHERE user_id = %s AND message_id = %s AND lease_token = %s AND status = 'processing'
                AND lease_until > NOW()""",
            (max_attempts, max_attempts, error_code, claim.context.user_id,
             claim.context.message_id, claim.lease_token))
