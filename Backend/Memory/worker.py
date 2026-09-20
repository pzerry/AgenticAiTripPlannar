"""Restartable database-inbox worker. Claim/finish transactions never span an LLM call."""

import argparse
import asyncio
import logging
import os
import time

from dotenv import load_dotenv
from psycopg_pool import AsyncConnectionPool

from Backend.Memory.events import EventRepository
from Backend.Memory.extractor import Extractor
from Backend.Memory.migrate import require_migrations
from Backend.Memory.persistence import LostLeaseError, apply_candidates

logger = logging.getLogger(__name__)


class MemoryWorker:
    def __init__(self, pool, extractor: Extractor, *, timeout_seconds: float = 60):
        if not 0 < timeout_seconds <= 60:
            raise ValueError("Extraction timeout must be between 0 and 60 seconds")
        self.pool = pool
        self.extractor = extractor
        self.timeout = timeout_seconds
        self.events = EventRepository()

    async def run_once(self) -> bool:
        async with self.pool.connection() as conn, conn.transaction():
            claim = await self.events.claim(conn)
        if claim is None:
            return False
        started = time.monotonic()
        try:
            async with asyncio.timeout(self.timeout):
                result = await self.extractor.extract(claim.context)
            async with self.pool.connection() as conn:
                counts = await apply_candidates(conn, claim, result.candidates)
            logger.info("memory_processed accepted=%d rejected=%d stale=%d latency_ms=%.1f usage=%s",
                        counts.accepted, counts.rejected, counts.stale,
                        (time.monotonic() - started) * 1000, result.usage)
        except LostLeaseError:
            logger.info("memory_result_discarded reason=lost_lease")
        except Exception as exc:
            category = ("timeout" if isinstance(exc, TimeoutError) else
                        "invalid_output" if isinstance(exc, ValueError) else "extraction_error")
            async with self.pool.connection() as conn, conn.transaction():
                await self.events.fail(conn, claim, error_code=category)
            logger.warning("memory_processing_failed category=%s attempt=%d latency_ms=%.1f",
                           category, claim.attempts, (time.monotonic() - started) * 1000)
        return True


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--provider", default=None)
    args = parser.parse_args()
    load_dotenv()
    # Lazy imports keep database/policy tests independent of provider credentials.
    from Backend.LLM.factory import get_llm
    from Backend.Memory.extractor import StructuredExtractor
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")
    async with AsyncConnectionPool(database_url, min_size=1, max_size=2, open=False) as pool:
        async with pool.connection() as conn:
            await require_migrations(conn)
        worker = MemoryWorker(pool, StructuredExtractor(get_llm(args.provider)))
        while True:
            worked = await worker.run_once()
            if args.once:
                break
            if not worked:
                await asyncio.sleep(1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
