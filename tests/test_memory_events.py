"""Real PostgreSQL acceptance tests for ordering, retries, and forgetting."""

import os
import unittest
from uuid import uuid4

from psycopg import AsyncConnection, sql

from Backend.Memory.contracts import EvidenceSpan, MemoryCandidate
from Backend.Memory.events import DuplicateMessageError, EventRepository, MessageInput, OwnershipError
from Backend.Memory.migrate import apply_migrations
from Backend.Memory.persistence import LostLeaseError, apply_candidates
from Backend.Memory.semantic_memory import SemanticMemoryRepository


@unittest.skipUnless(os.getenv("MEMORY_TEST_DATABASE_URL"), "No test PostgreSQL URL")
class EventTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.conn = await AsyncConnection.connect(os.environ["MEMORY_TEST_DATABASE_URL"])
        self.addAsyncCleanup(self.conn.close)
        self.addAsyncCleanup(self.conn.rollback)
        self.schema = "events_test_" + uuid4().hex
        await self.conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema)))
        await self.conn.execute(sql.SQL("SET LOCAL search_path TO {}").format(sql.Identifier(self.schema)))
        await apply_migrations(self.conn)
        self.events = EventRepository()
        self.memory = SemanticMemoryRepository()
        self.user = uuid4()

    async def capture(self, text="I always prefer nonstop flights.", **patch):
        message = MessageInput(**(dict(user_id=self.user, message_id=uuid4(),
                                       thread_id="thread-a", text=text) | patch))
        return message, await self.events.capture(self.conn, message)

    def candidate(self, claim, *, operation="upsert", value="non_stop", **patch):
        text = claim.context.text
        return MemoryCandidate(**(dict(operation=operation, memory_key="preferred_flight_type",
            memory_value=value, subject="self", scope="durable", assertion="explicit",
            evidence=EvidenceSpan(start=0, end=len(text), quote=text)) | patch))

    async def test_migrations_are_tracked_and_rerunnable(self):
        await apply_migrations(self.conn)
        cur = await self.conn.execute("SELECT count(*) FROM memory_schema_migrations")
        self.assertEqual((await cur.fetchone())[0], 3)

    async def test_stable_capture_and_payload_conflict(self):
        message, first = await self.capture()
        second = await self.events.capture(self.conn, message)
        self.assertEqual(first.sequence, second.sequence)
        with self.assertRaises(DuplicateMessageError):
            await self.events.capture(self.conn, message.model_copy(update={"text": "Different"}))
        _, third = await self.capture(thread_id="thread-b")
        self.assertEqual(third.sequence, first.sequence + 1)

    async def test_cannot_claim_other_users_thread(self):
        await self.capture()
        with self.assertRaises(OwnershipError):
            await self.capture(user_id=uuid4())

    async def test_claim_does_not_redeliver_active_lease(self):
        await self.capture()
        self.assertIsNotNone(await self.events.claim(self.conn))
        self.assertIsNone(await self.events.claim(self.conn))

    async def test_correction_wins_over_delayed_result(self):
        await self.capture()
        old = await self.events.claim(self.conn)
        await self.capture("From now on connections are generally fine.")
        new = await self.events.claim(self.conn)
        await apply_candidates(self.conn, new, [self.candidate(new, value="connecting_allowed")])
        result = await apply_candidates(self.conn, old, [self.candidate(old)])
        self.assertEqual(result.stale, 1)
        memory = await self.memory.get(self.conn, user_id=self.user, memory_key="preferred_flight_type")
        self.assertEqual(memory.memory_value, "connecting_allowed")

    async def test_forgetting_fences_old_work_but_allows_new_explicit_preference(self):
        message, _ = await self.capture()
        old = await self.events.claim(self.conn)
        await self.capture("Forget my flight preference.")
        deletion = await self.events.claim(self.conn)
        await apply_candidates(self.conn, deletion, [self.candidate(deletion, operation="delete", value=None)])
        result = await apply_candidates(self.conn, old, [self.candidate(old)])
        self.assertEqual(result.stale, 1)
        self.assertEqual(await self.memory.get_all(self.conn, user_id=self.user), [])
        replay = await self.events.capture(self.conn, message)
        self.assertEqual(replay.status, "complete")
        self.assertIsNone(await self.events.claim(self.conn))
        await self.capture("I now always prefer nonstop flights.")
        fresh = await self.events.claim(self.conn)
        await apply_candidates(self.conn, fresh, [self.candidate(fresh)])
        self.assertEqual(len(await self.memory.get_all(self.conn, user_id=self.user)), 1)

    async def test_evidence_is_checked_against_stored_source(self):
        await self.capture("For this trip, connections are fine.")
        claim = await self.events.claim(self.conn)
        fake = claim.model_copy(update={"context": claim.context.model_copy(
            update={"text": "I always prefer nonstop flights."})})
        result = await apply_candidates(self.conn, fake, [self.candidate(fake)])
        self.assertEqual(result.rejected, 1)
        self.assertEqual(await self.memory.get_all(self.conn, user_id=self.user), [])

    async def test_trip_only_and_other_subject_do_not_write(self):
        for patch in ({"scope": "trip"}, {"subject": "other"}, {"assertion": "inferred"}):
            await self.capture()
            claim = await self.events.claim(self.conn)
            result = await apply_candidates(self.conn, claim, [self.candidate(claim, **patch)])
            self.assertEqual(result.rejected, 1)
        self.assertEqual(await self.memory.get_all(self.conn, user_id=self.user), [])

    async def test_expired_worker_cannot_write(self):
        await self.capture()
        old = await self.events.claim(self.conn)
        await self.conn.execute("UPDATE memory_events SET lease_until = NOW() - INTERVAL '1 second'")
        fresh = await self.events.claim(self.conn)
        with self.assertRaises(LostLeaseError):
            await apply_candidates(self.conn, old, [self.candidate(old)])
        result = await apply_candidates(self.conn, fresh, [self.candidate(fresh)])
        self.assertEqual(result.accepted, 1)

    async def test_completion_scrubs_text_and_rejects_second_apply(self):
        await self.capture()
        claim = await self.events.claim(self.conn)
        await apply_candidates(self.conn, claim, [])
        cur = await self.conn.execute("SELECT source_text, status FROM memory_events")
        self.assertEqual(await cur.fetchone(), (None, "complete"))
        with self.assertRaises(LostLeaseError):
            await apply_candidates(self.conn, claim, [self.candidate(claim)])

    async def test_duplicate_candidates_leave_event_uncommitted(self):
        await self.capture()
        claim = await self.events.claim(self.conn)
        candidate = self.candidate(claim)
        with self.assertRaises(ValueError):
            await apply_candidates(self.conn, claim, [candidate, candidate])
        cur = await self.conn.execute("SELECT status FROM memory_events")
        self.assertEqual((await cur.fetchone())[0], "processing")

    async def test_exhausted_crash_and_expiration_scrub_payload(self):
        await self.capture()
        await self.events.claim(self.conn)
        await self.conn.execute("""UPDATE memory_events SET attempts = 3,
            lease_until = NOW() - INTERVAL '1 second'""")
        self.assertIsNone(await self.events.claim(self.conn))
        cur = await self.conn.execute("SELECT status, source_text FROM memory_events")
        self.assertEqual(await cur.fetchone(), ("failed", None))
        await self.capture()
        await self.conn.execute("UPDATE memory_events SET expires_at = NOW() - INTERVAL '1 second'")
        self.assertIsNone(await self.events.claim(self.conn))
        cur = await self.conn.execute("SELECT count(*) FROM memory_events WHERE source_text IS NOT NULL")
        self.assertEqual((await cur.fetchone())[0], 0)

    async def test_isolation_after_apply(self):
        await self.capture()
        claim = await self.events.claim(self.conn)
        await apply_candidates(self.conn, claim, [self.candidate(claim)])
        self.assertEqual(await self.memory.get_all(self.conn, user_id=uuid4()), [])
