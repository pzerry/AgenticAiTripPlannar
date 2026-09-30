import asyncio
import os
from uuid import uuid4

from dotenv import load_dotenv
from psycopg_pool import AsyncConnectionPool

from Backend.LLM.factory import get_llm
from Backend.Memory.events import EventRepository, MessageInput
from Backend.Memory.extractor import StructuredExtractor
from Backend.Memory.migrate import require_migrations
from Backend.Memory.semantic_memory import SemanticMemoryRepository
from Backend.Memory.worker import MemoryWorker


PROVIDER = "groq"


async def capture_message(
    pool,
    *,
    user_id,
    thread_id,
    message_id,
    text,
):
    async with pool.connection() as conn:
        async with conn.transaction():
            event = await EventRepository().capture(
                conn,
                MessageInput(
                    user_id=user_id,
                    message_id=message_id,
                    thread_id=thread_id,
                    text=text,
                ),
            )

    print(
        f"Captured message_id={message_id} "
        f"sequence={event.sequence} "
        f"status={event.status}"
    )

    return event


async def get_event_status(
    pool,
    *,
    user_id,
    message_id,
):
    async with pool.connection() as conn:
        cursor = await conn.execute(
            """
            SELECT status, attempts, error_code
            FROM memory_events
            WHERE user_id = %s
              AND message_id = %s
            """,
            (user_id, message_id),
        )

        return await cursor.fetchone()


async def process_until_complete(
    pool,
    worker,
    *,
    user_id,
    message_id,
    max_runs=30,
):
    for run_number in range(1, max_runs + 1):
        row = await get_event_status(
            pool,
            user_id=user_id,
            message_id=message_id,
        )

        if row is None:
            raise RuntimeError(
                f"Event not found: {message_id}"
            )

        status, attempts, error_code = row

        print(
            f"Run {run_number}: "
            f"status={status}, "
            f"attempts={attempts}, "
            f"error={error_code}"
        )

        if status in {
            "complete",
            "failed",
            "expired",
        }:
            return row

        worked = await worker.run_once()

        print(
            "worker.run_once() ->",
            worked,
        )

        if not worked:
            await asyncio.sleep(1)

    raise RuntimeError(
        f"Event {message_id} did not finish"
    )


async def get_memory(
    pool,
    *,
    user_id,
):
    async with pool.connection() as conn:
        return await SemanticMemoryRepository().get(
            conn,
            user_id=user_id,
            memory_key="preferred_flight_type",
        )


async def count_active_memories(
    pool,
    *,
    user_id,
):
    async with pool.connection() as conn:
        cursor = await conn.execute(
            """
            SELECT COUNT(*)
            FROM semantic_memories
            WHERE user_id = %s
              AND memory_key = 'preferred_flight_type'
            """,
            (user_id,),
        )

        row = await cursor.fetchone()

    return row[0]


async def main():
    load_dotenv()

    database_url = os.environ.get(
        "DATABASE_URL"
    )

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is not configured"
        )

    user_id = uuid4()
    thread_id = f"idempotency-test-{uuid4()}"

    # IMPORTANT:
    # We deliberately reuse the SAME message_id.
    message_id = uuid4()

    text = (
        "I always prefer nonstop flights."
    )

    print("=" * 80)
    print("DUPLICATE / IDEMPOTENCY TEST")
    print("=" * 80)

    print("User:", user_id)
    print("Message ID:", message_id)

    llm = get_llm(
        PROVIDER
    )

    extractor = StructuredExtractor(
        llm,
        method="json_mode",
    )

    async with AsyncConnectionPool(
        database_url,
        min_size=1,
        max_size=3,
        open=False,
    ) as pool:

        async with pool.connection() as conn:
            await require_migrations(conn)

        worker = MemoryWorker(
            pool,
            extractor,
            timeout_seconds=60,
        )

        # =========================================================
        # TEST 1
        # Capture and process original event
        # =========================================================

        print(
            "\n### STEP 1: FIRST CAPTURE ###"
        )

        first_event = await capture_message(
            pool,
            user_id=user_id,
            thread_id=thread_id,
            message_id=message_id,
            text=text,
        )

        first_status = await process_until_complete(
            pool,
            worker,
            user_id=user_id,
            message_id=message_id,
        )

        print(
            "First processing status:",
            first_status,
        )

        assert first_status[0] == "complete"

        memory = await get_memory(
            pool,
            user_id=user_id,
        )

        assert memory is not None

        assert (
            memory.memory_value == "non_stop"
        )

        original_memory_id = memory.id
        original_updated_at = memory.updated_at

        print(
            "[PASS] First event saved memory"
        )

        print(
            "Memory ID:",
            original_memory_id,
        )

        # =========================================================
        # TEST 2
        # Try to capture SAME message again
        # =========================================================

        print(
            "\n### STEP 2: DUPLICATE CAPTURE ###"
        )

        try:
            duplicate_event = await capture_message(
                pool,
                user_id=user_id,
                thread_id=thread_id,
                message_id=message_id,
                text=text,
            )

            print(
                "Duplicate capture returned:",
                duplicate_event,
            )

        except Exception as exc:
            print(
                "Duplicate capture rejected:",
                type(exc).__name__,
                str(exc),
            )

        # Regardless of how duplicate capture is handled,
        # there must still be exactly one active semantic memory.

        count = await count_active_memories(
            pool,
            user_id=user_id,
        )

        print(
            "Active preferred_flight_type rows:",
            count,
        )

        assert count == 1, (
            f"Expected exactly 1 active memory, got {count}"
        )

        # =========================================================
        # TEST 3
        # Simulate retry by putting SAME event back to pending
        # =========================================================

        print(
            "\n### STEP 3: SIMULATED RETRY ###"
        )

        async with pool.connection() as conn:
            async with conn.transaction():
                await conn.execute(
                    """
                    UPDATE memory_events
                    SET
                        status = 'pending',
                        available_at = NOW(),
                        error_code = NULL
                    WHERE user_id = %s
                      AND message_id = %s
                    """,
                    (user_id, message_id),
                )

        print(
            "Same event manually returned to pending."
        )

        retry_status = await process_until_complete(
            pool,
            worker,
            user_id=user_id,
            message_id=message_id,
        )

        print(
            "Retry processing status:",
            retry_status,
        )

        assert retry_status[0] == "complete"

        # =========================================================
        # FINAL MEMORY CHECK
        # =========================================================

        final_memory = await get_memory(
            pool,
            user_id=user_id,
        )

        assert final_memory is not None

        assert (
            final_memory.memory_value
            == "non_stop"
        )

        final_count = await count_active_memories(
            pool,
            user_id=user_id,
        )

        assert final_count == 1, (
            "Duplicate processing created duplicate memory rows"
        )

        print(
            "\nFinal memory:",
            final_memory.memory_key,
            "=",
            final_memory.memory_value,
        )

        print(
            "Final memory ID:",
            final_memory.id,
        )

        print(
            "Active row count:",
            final_count,
        )

        # Ideally the same logical memory row should remain.
        assert (
            final_memory.id == original_memory_id
        ), (
            "Retry unexpectedly created a new semantic memory row"
        )

        print()
        print("=" * 80)
        print(
            "[PASS] IDEMPOTENCY / RETRY PROTECTION WORKS"
        )
        print(
            "Exactly one active memory remains"
        )
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(
        main()
    )