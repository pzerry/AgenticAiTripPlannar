"""Coordinate HTTP retries with the memory inbox and graph checkpoints.

The database transaction covers only capture/receipts. A session advisory lock
serializes one conversation across API processes while the graph calls models.
The durable active_message_id handles a crash after that lock disappears.
"""

from contextlib import asynccontextmanager
import hashlib

from psycopg.types.json import Jsonb

from Backend.Memory.events import EventRepository, MessageInput, OwnershipError
from Backend.Memory.retrieval import retrieve_preferences


class TurnBusyError(ValueError):
    """Another message is running or needs to be retried first."""


@asynccontextmanager
async def thread_guard(pool, *, user_id, thread_id):
    # Do not use Python hash(): it changes between API processes. Collisions
    # only serialize unrelated threads; ownership still uses the full thread ID.
    key = int.from_bytes(hashlib.sha256(thread_id.encode()).digest()[:4], "big", signed=True)
    async with pool.connection() as conn:
        if not conn.autocommit:
            raise ValueError("Chat coordination requires an autocommit connection pool")
        cur = await conn.execute("SELECT pg_try_advisory_lock(731902, %s)", (key,))
        if not (await cur.fetchone())[0]:
            raise TurnBusyError("This conversation is busy; retry the same message ID")
        try:
            cur = await conn.execute("SELECT user_id FROM memory_threads WHERE thread_id = %s", (thread_id,))
            row = await cur.fetchone()
            if row and row[0] != user_id:
                raise OwnershipError("Thread is not owned by this user")
            yield conn
        finally:
            # A pooled session must never be returned with our lock still held.
            try:
                await conn.execute("SELECT pg_advisory_unlock(731902, %s)", (key,))
            except BaseException:
                await conn.close()
                raise


async def begin_turn(conn, message: MessageInput) -> tuple[dict, list, dict | None]:
    """Capture once and freeze this turn's retrieved defaults for crash retries."""
    async with conn.transaction():
        await EventRepository().capture(conn, message)
        cur = await conn.execute("""SELECT memory_context, memory_selected_ids, response
            FROM chat_turn_receipts WHERE user_id = %s AND message_id = %s""",
            (message.user_id, message.message_id))
        receipt = await cur.fetchone()
        if receipt and receipt[2] is not None:
            # Return even when a later turn is interrupted. Replaying this old
            # response must never consume the later question's interrupt.
            return receipt
        cur = await conn.execute("SELECT active_message_id FROM memory_threads WHERE thread_id = %s",
                                 (message.thread_id,))
        active = (await cur.fetchone())[0]
        if active is not None and active != message.message_id:
            raise TurnBusyError(f"Retry unfinished message {active} before sending another message")
        if receipt is None:
            memory = await retrieve_preferences(conn, user_id=message.user_id)
            receipt = (memory.preferences, list(memory.selected_ids), None)
            await conn.execute("""INSERT INTO chat_turn_receipts
                (user_id, message_id, thread_id, memory_context, memory_selected_ids)
                VALUES (%s, %s, %s, %s, %s)""", (message.user_id, message.message_id,
                    message.thread_id, Jsonb(receipt[0]), Jsonb(receipt[1])))
        await conn.execute("UPDATE memory_threads SET active_message_id = %s WHERE thread_id = %s",
                           (message.message_id, message.thread_id))
        return receipt


async def finish_turn(conn, message: MessageInput, response: dict) -> None:
    """Publish the replayable response and release the conversation atomically."""
    async with conn.transaction():
        await conn.execute("""UPDATE chat_turn_receipts SET response = %s,
            memory_context = '{}'::jsonb, memory_selected_ids = '[]'::jsonb
            WHERE user_id = %s AND message_id = %s""",
            (Jsonb(response), message.user_id, message.message_id))
        await conn.execute("""UPDATE memory_threads SET active_message_id = NULL
            WHERE thread_id = %s AND user_id = %s AND active_message_id = %s""",
            (message.thread_id, message.user_id, message.message_id))


async def event_status(conn, *, user_id, message_id) -> str | None:
    cur = await conn.execute("SELECT status FROM memory_events WHERE user_id = %s AND message_id = %s",
                             (user_id, message_id))
    row = await cur.fetchone()
    return row[0] if row else None
