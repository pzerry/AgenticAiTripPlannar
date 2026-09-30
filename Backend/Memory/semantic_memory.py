"""Async PostgreSQL repository. The caller owns connections and transactions."""

from uuid import UUID, uuid4

from psycopg import AsyncConnection
from psycopg.rows import dict_row

from Backend.Memory.models import MemoryKey, SemanticMemory, SemanticMemoryInput


class SemanticMemoryRepository:
    """One active value per user/key; last accepted write wins.

    No LLM calls, environment loading, implicit commits, or table creation.
    Every read/write requires a user identity supplied by the application.
    """

    async def save(self, conn: AsyncConnection, memory: SemanticMemoryInput) -> SemanticMemory:
        # Revalidate even objects constructed without validation by other code.
        memory = SemanticMemoryInput.model_validate(memory.model_dump())
        async with conn.cursor(row_factory=dict_row) as cursor:
            await cursor.execute(
                """
                INSERT INTO semantic_memories
                    (id, user_id, memory_key, memory_value, confidence, source_thread_id)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id, memory_key) DO UPDATE SET
                    memory_value = EXCLUDED.memory_value,
                    confidence = EXCLUDED.confidence,
                    source_thread_id = EXCLUDED.source_thread_id,
                    updated_at = clock_timestamp()
                RETURNING *
                """,
                (uuid4(), memory.user_id, memory.memory_key, memory.memory_value,
                 memory.confidence, memory.source_thread_id),
            )
            row = await cursor.fetchone()
        if row is None:
            raise RuntimeError("Semantic memory save returned no row")
        return SemanticMemory.model_validate(row)

    async def get(self, conn: AsyncConnection, *, user_id: UUID,
                  memory_key: MemoryKey) -> SemanticMemory | None:
        async with conn.cursor(row_factory=dict_row) as cursor:
            await cursor.execute(
                "SELECT * FROM semantic_memories WHERE user_id = %s AND memory_key = %s",
                (user_id, memory_key),
            )
            row = await cursor.fetchone()
        return SemanticMemory.model_validate(row) if row is not None else None

    async def get_all(self, conn: AsyncConnection, *, user_id: UUID) -> list[SemanticMemory]:
        async with conn.cursor(row_factory=dict_row) as cursor:
            await cursor.execute(
                "SELECT * FROM semantic_memories WHERE user_id = %s ORDER BY memory_key",
                (user_id,),
            )
            rows = await cursor.fetchall()
        return [SemanticMemory.model_validate(row) for row in rows]

    async def delete(self, conn: AsyncConnection, *, user_id: UUID,
                     memory_key: MemoryKey) -> bool:
        async with conn.cursor() as cursor:
            await cursor.execute(
                "DELETE FROM semantic_memories WHERE user_id = %s AND memory_key = %s RETURNING id",
                (user_id, memory_key),
            )
            return await cursor.fetchone() is not None
