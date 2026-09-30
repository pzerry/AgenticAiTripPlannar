from __future__ import annotations

import asyncpg

from Backend.Config.env import env


_pool: asyncpg.Pool | None = None


async def create_db_pool() -> asyncpg.Pool:
    """Create the PostgreSQL connection pool."""

    global _pool

    if _pool is not None:
        return _pool

    database_url = env.DATABASE_URL

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is not configured."
        )

    _pool = await asyncpg.create_pool(
        dsn=database_url,
        min_size=1,
        max_size=10,
        command_timeout=30,
    )

    return _pool


async def get_db_pool() -> asyncpg.Pool:
    """Return the active PostgreSQL connection pool."""

    if _pool is None:
        return await create_db_pool()

    return _pool


async def close_db_pool() -> None:
    """Close the PostgreSQL connection pool."""

    global _pool

    if _pool is not None:
        await _pool.close()
        _pool = None