"""Committed multi-connection tests; no application database is used."""

import asyncio
import os
import unittest
from uuid import uuid4

from psycopg import AsyncConnection, sql
from psycopg_pool import AsyncConnectionPool

from Backend.Memory.events import EventRepository, MessageInput
from Backend.Memory.extractor import ExtractionResult
from Backend.Memory.migrate import apply_migrations
from Backend.Memory.worker import MemoryWorker


@unittest.skipUnless(os.getenv("MEMORY_TEST_DATABASE_URL"), "No test PostgreSQL URL")
class ConcurrencyTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.url = os.environ["MEMORY_TEST_DATABASE_URL"]
        self.schema = "concurrent_memory_" + uuid4().hex
        self.admin = await AsyncConnection.connect(self.url, autocommit=True)
        self.addAsyncCleanup(self.admin.close)
        await self.admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema)))
        self.addAsyncCleanup(self.drop_schema)
        await self.admin.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(self.schema)))
        await apply_migrations(self.admin)
        self.pool = AsyncConnectionPool(self.url, min_size=1, max_size=4, open=False,
            kwargs={"options": f"-c search_path={self.schema}"})
        await self.pool.open()
        self.addAsyncCleanup(self.pool.close)
        self.events = EventRepository()
        self.user = uuid4()

    async def drop_schema(self):
        # Only the random schema this test created is removed.
        await self.admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(self.schema)))

    async def capture(self, message):
        async with self.pool.connection() as conn, conn.transaction():
            return await self.events.capture(conn, message)

    async def claim(self):
        async with self.pool.connection() as conn, conn.transaction():
            return await self.events.claim(conn)

    def message(self, **patch):
        return MessageInput(**(dict(user_id=self.user, message_id=uuid4(), thread_id="a",
                                   text="I always prefer nonstop flights.") | patch))

    async def test_concurrent_duplicate_capture_has_one_sequence(self):
        message = self.message()
        results = await asyncio.gather(*(self.capture(message) for _ in range(4)))
        self.assertEqual({r.sequence for r in results}, {1})
        cur = await self.admin.execute("SELECT count(*) FROM memory_events")
        self.assertEqual((await cur.fetchone())[0], 1)

    async def test_concurrent_workers_claim_distinct_events(self):
        await asyncio.gather(*(self.capture(self.message()) for _ in range(4)))
        claims = await asyncio.gather(*(self.claim() for _ in range(4)))
        self.assertEqual(len({c.context.message_id for c in claims}), 4)
        self.assertEqual({c.context.sequence for c in claims}, {1, 2, 3, 4})

    async def test_worker_model_failure_is_durable_and_redacted(self):
        class FailingExtractor:
            async def extract(self, context):
                raise RuntimeError("private source text must not be logged")
        await self.capture(self.message())
        with self.assertLogs("Backend.Memory.worker", level="WARNING") as logs:
            self.assertTrue(await MemoryWorker(self.pool, FailingExtractor()).run_once())
        self.assertNotIn("private source", str(logs.output))
        cur = await self.admin.execute("SELECT status, attempts, error_code FROM memory_events")
        self.assertEqual(await cur.fetchone(), ("pending", 1, "extraction_error"))

    async def test_worker_timeout_and_success(self):
        class SlowExtractor:
            async def extract(self, context):
                await asyncio.sleep(1)
        class EmptyExtractor:
            async def extract(self, context):
                return ExtractionResult([])
        await self.capture(self.message())
        await MemoryWorker(self.pool, SlowExtractor(), timeout_seconds=0.01).run_once()
        cur = await self.admin.execute("SELECT error_code FROM memory_events")
        self.assertEqual((await cur.fetchone())[0], "timeout")
        await self.admin.execute("UPDATE memory_events SET available_at = NOW()")
        await MemoryWorker(self.pool, EmptyExtractor()).run_once()
        cur = await self.admin.execute("SELECT status, source_text FROM memory_events")
        self.assertEqual(await cur.fetchone(), ("complete", None))
