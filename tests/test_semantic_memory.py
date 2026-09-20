"""Run: python -m unittest discover -s tests -v.

Set MEMORY_TEST_DATABASE_URL to enable PostgreSQL tests. Each test uses an
isolated schema and rolls back all its changes, including schema creation.
"""
import os
import unittest
from uuid import uuid4

from pydantic import ValidationError
from psycopg import AsyncConnection, sql

from Backend.Memory.migrate import MIGRATION
from Backend.Memory.models import SemanticMemoryInput
from Backend.Memory.semantic_memory import SemanticMemoryRepository


class ValidationTests(unittest.TestCase):
    def test_rejects_invalid_memories(self):
        valid = dict(user_id=uuid4(), memory_key="preferred_flight_type",
                     memory_value="non_stop", source_thread_id="thread-1")
        for patch in (
            {"confidence": -0.1}, {"confidence": 1.1}, {"confidence": float("nan")},
            {"memory_key": "destination"}, {"memory_value": "5_star"},
            {"source_thread_id": " "}, {"user_id": "invalid"}, {"extra": "field"},
        ):
            with self.subTest(patch=patch), self.assertRaises(ValidationError):
                SemanticMemoryInput(**(valid | patch))


@unittest.skipUnless(os.getenv("MEMORY_TEST_DATABASE_URL"), "No test PostgreSQL URL")
class RepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.conn = await AsyncConnection.connect(os.environ["MEMORY_TEST_DATABASE_URL"])
        self.addAsyncCleanup(self.conn.close)
        self.addAsyncCleanup(self.conn.rollback)
        schema = "memory_test_" + uuid4().hex
        await self.conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        await self.conn.execute(sql.SQL("SET LOCAL search_path TO {}").format(sql.Identifier(schema)))
        await self.conn.execute(MIGRATION.read_text())
        await self.conn.execute(MIGRATION.read_text())  # rerunnable initial migration
        self.repo = SemanticMemoryRepository()
        self.user = uuid4()

    def memory(self, **patch):
        return SemanticMemoryInput(**(dict(user_id=self.user,
            memory_key="preferred_hotel_class", memory_value="4_star",
            source_thread_id="trip-a") | patch))

    async def test_upsert_and_cross_thread_read(self):
        first = await self.repo.save(self.conn, self.memory())
        second = await self.repo.save(self.conn, self.memory(
            memory_value="5_star", source_thread_id="trip-b"))
        self.assertEqual(first.id, second.id)
        self.assertEqual(first.created_at, second.created_at)
        self.assertGreaterEqual(second.updated_at, first.updated_at)
        rows = await self.repo.get_all(self.conn, user_id=self.user)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].memory_value, "5_star")
        self.assertEqual(rows[0].source_thread_id, "trip-b")

    async def test_user_isolation_and_delete(self):
        other = uuid4()
        await self.repo.save(self.conn, self.memory())
        self.assertIsNone(await self.repo.get(self.conn, user_id=other,
                                             memory_key="preferred_hotel_class"))
        self.assertEqual(await self.repo.get_all(self.conn, user_id=other), [])
        self.assertFalse(await self.repo.delete(self.conn, user_id=other,
                                                memory_key="preferred_hotel_class"))
        await self.repo.save(self.conn, self.memory(user_id=other, memory_value="3_star"))
        self.assertTrue(await self.repo.delete(self.conn, user_id=self.user,
                                               memory_key="preferred_hotel_class"))
        self.assertFalse(await self.repo.delete(self.conn, user_id=self.user,
                                                memory_key="preferred_hotel_class"))
        remaining = await self.repo.get(self.conn, user_id=other,
                                        memory_key="preferred_hotel_class")
        self.assertEqual(remaining.memory_value, "3_star")

    async def test_database_rejects_invalid_confidence(self):
        from psycopg.errors import CheckViolation
        with self.assertRaises(CheckViolation):
            await self.conn.execute(
                """INSERT INTO semantic_memories
                (id, user_id, memory_key, memory_value, confidence, source_thread_id)
                VALUES (%s, %s, 'preferred_hotel_class', '4_star', 2, 'test')""",
                (uuid4(), self.user))
