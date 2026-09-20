"""Run with: python -m Backend.Memory.migrate (uses DATABASE_URL)."""

import asyncio
import hashlib
import os
from pathlib import Path

from dotenv import load_dotenv
from psycopg import AsyncConnection

MIGRATION = Path(__file__).parent / "migrations" / "001_semantic_memories.sql"


async def require_migrations(conn: AsyncConnection) -> None:
    """Fail startup with an actionable message; do not run schema DDL in chat."""
    cur = await conn.execute("SELECT to_regclass('memory_schema_migrations')")
    if (await cur.fetchone())[0] is None:
        raise RuntimeError("Run python -m Backend.Memory.migrate before starting the API")
    cur = await conn.execute("SELECT name, checksum FROM memory_schema_migrations")
    applied = dict(await cur.fetchall())
    for path in sorted(MIGRATION.parent.glob("[0-9]*.sql")):
        if applied.get(path.name) != hashlib.sha256(path.read_text().encode()).hexdigest():
            raise RuntimeError("Memory schema is outdated; run python -m Backend.Memory.migrate")


async def apply_migrations(conn: AsyncConnection) -> None:
    """Apply numbered migrations atomically, with checksums and a process lock."""
    async with conn.transaction():
        await conn.execute("SELECT pg_advisory_xact_lock(731901, 1)")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS memory_schema_migrations (
                name TEXT PRIMARY KEY,
                checksum TEXT NOT NULL,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        for path in sorted(MIGRATION.parent.glob("[0-9]*.sql")):
            content = path.read_text()
            checksum = hashlib.sha256(content.encode()).hexdigest()
            cursor = await conn.execute(
                "SELECT checksum FROM memory_schema_migrations WHERE name = %s", (path.name,)
            )
            previous = await cursor.fetchone()
            if previous:
                if previous[0] != checksum:
                    raise RuntimeError(f"Applied migration changed: {path.name}")
                continue
            await conn.execute(content)
            await conn.execute(
                "INSERT INTO memory_schema_migrations (name, checksum) VALUES (%s, %s)",
                (path.name, checksum),
            )


async def main() -> None:
    load_dotenv()
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")
    async with await AsyncConnection.connect(database_url) as conn:
        await apply_migrations(conn)
    print("Memory migrations applied.")


if __name__ == "__main__":
    asyncio.run(main())
