# Trip planner: long-term memory architecture

Reference: [Design Memory Architecture discussion](https://chatgpt.com/share/6a9e48f9-2a78-83e8-9204-9be82131aedb).

## Scope and current status

The product goal is an end-to-end AI trip planner that produces an itinerary with reasons. Build it incrementally, explaining each component. Short-term memory uses PostgreSQL-backed LangGraph checkpoints keyed by thread_id. Clarification now has its own checkpointed graph node.

As of 2026-09-13, the authenticated API captures messages, retrieves preferences, and passes them to the planner. Clarification answers and assistant responses are persisted. A separate worker processes captured messages. The UI supports account tokens, stable retries, and preference inspection/deletion. This integration is verified with real PostgreSQL and deterministic model responses; live model quality and deployment remain unverified. No application database migration has been executed. See the [code walkthrough and startup instructions](memory-integration-walkthrough.md) and [completion checklist](memory-completion-checklist.md).

## Design decisions

- Use PostgreSQL, already present in the project. Use psycopg async connections, matching the existing checkpoint graph. The existing asyncpg helper is a different driver and cannot supply a connection to this repository.
- Keep checkpoint state separate from semantic_memories. A new thread for the same user can retrieve preferences without inheriting an old trip's dates or destination.
- Begin with three supported keys: preferred_flight_type, preferred_hotel_class, preferred_trip_style. Values are bounded enums validated by Pydantic and database constraints. Adding keys requires a model change and a new database migration.
- Store one active value per (user_id, memory_key). The production write boundary is now `apply_candidates`, which uses server-assigned per-user event order. A delayed result cannot replace a newer correction. Deletion retains an ordering record without the old preference value. The low-level repository remains an implementation detail; calling its save/delete methods directly bypasses these protections.
- Store confidence as metadata only. It is not a calibrated probability and must not authorize writes by itself.
- Store source_thread_id for provenance, but do not duplicate full conversations or sensitive evidence in this table.
- Repository operations use parameterized SQL. Connections and transaction boundaries belong to the caller. Table creation runs separately as a migration, not in each graph invocation.

## Memory admission policy

“I always prefer nonstop flights” is a durable preference candidate. “Find nonstop flights for this trip” only modifies the current trip. Dates, destinations, prices, weather, and an individual trip's budget are not durable preferences. An assistant suggestion or a tool result is not evidence of a user's preference.

Explicit current requests override saved preferences. Saved preferences may fill missing values, but must not overwrite current trip decisions. The extractor must support corrections and explicit forgetting, with tests before it is enabled. A deleted preference must not be recreated by replaying older messages.

The allowlisted schema limits stored content but cannot determine whether a statement is durable; extraction and policy handle that classification, with live evaluation still required.

## Files and usage

- Backend/Memory/models.py: validated input and persisted record.
- Backend/Memory/semantic_memory.py: save, get, get_all, and delete.
- Backend/Memory/migrations/001_semantic_memories.sql: initial table and constraints.
- Backend/Memory/migrate.py: explicit transactional migration entry point.
- tests/test_semantic_memory.py: validation and opt-in real PostgreSQL tests.
- Backend/Memory/events.py: message idempotency, thread ownership records, per-user ordering, and durable worker claims with leases.
- Backend/Memory/persistence.py: validates evidence against stored source, applies policy, fences stale writes, and atomically completes events.
- Backend/Memory/extractor.py: structured model adapter and exact quote validation; has no database access.
- Backend/Memory/prompts/extract_preferences.md: version-controlled extraction policy and travel examples.
- Backend/Memory/worker.py: bounded extraction, retries, timeout, and redacted outcome logging.
- Backend/Memory/migrations/002_memory_events.sql: durable inbox and revision/tombstone records.
- Backend/Memory/migrations/003_chat_turns.sql: response receipts and unfinished-turn tracking.
- Backend/Memory/chat_turns.py: conversation locking, capture/retrieval transactions, and replay.
- Backend/Memory/management.py: explicit deletion through the ordered write boundary.
- Backend/Graph/nodes/conversation.py: clarification node and assistant-message persistence.
- Backend/Graph/checkpoint.py: explicit serializer allowlist for persisted travel models.
- app/services/travel_service.py: ownership, retrieval, graph invocation, and turn recovery.
- Backend/Memory/evaluate.py and evals/memory/: synthetic live model evaluation and separate Mem0 probe.

Apply all numbered migrations to the intended development database from the project root:

```sh
.venv/bin/python -m Backend.Memory.migrate
```

It reads DATABASE_URL from the environment or .env. Numbered migrations are recorded with checksums and applied under a PostgreSQL transaction and advisory lock. Re-running skips unchanged applied migrations and rejects edits to previously applied migration files. Migration 001 still permits adoption of the original table; an incompatible pre-existing schema requires explicit reconciliation.

Example inside an async function with a psycopg pool supplied by the application:

```python
from uuid import UUID
from Backend.Memory.models import SemanticMemoryInput
from Backend.Memory.semantic_memory import SemanticMemoryRepository

repository = SemanticMemoryRepository()
async with pool.connection() as conn:
    async with conn.transaction():
        saved = await repository.save(conn, SemanticMemoryInput(
            user_id=UUID("00000000-0000-0000-0000-000000000001"),
            memory_key="preferred_flight_type",
            memory_value="non_stop",
            source_thread_id="example-thread",
        ))
        memories = await repository.get_all(conn, user_id=saved.user_id)
```

This low-level example demonstrates storage only. Automatic processing must use event capture, extraction, and `apply_candidates`; it must not call this repository directly.

## Event and worker lifecycle

The authenticated API captures each user message before planning, including clarification answers. A stable message_id is required across client retries. Reusing it with different text or a different thread is rejected. PostgreSQL serializes the short capture transaction for each user to allocate a durable sequence. No model call runs under that lock.

Workers claim pending messages using `FOR UPDATE SKIP LOCKED`, commit the claim, and release the database connection before calling a model. Leases last 90 seconds; model calls time out at 60 seconds. A worker can finish only while it still owns an unexpired lease. Crashed work becomes eligible after its lease expires, with at most three attempts. Failures use bounded backoff. Exhausted jobs become terminal failures.

Policy and persistence run in one transaction. Evidence offsets are computed in Python from an exact unique quote, then checked again against the original stored message at write time. The extractor's subject and scope predictions remain fallible and require live evaluation; exact quotes alone do not prove semantic correctness.

Successful processing removes source_text from the inbox. Expired or exhausted jobs are also scrubbed when the worker polls. Pending payloads expire after seven days. Continuous worker operation is necessary to enforce timely cleanup. The payload digest, message identity, and revision tombstones remain for idempotency and stale-write rejection; these are still user-associated metadata. This does not delete the separate LangGraph checkpoint history or backups. Full account erasure and checkpoint retention require the lifecycle work in the completion checklist.

After migrations, a worker can be run separately from the API:

```sh
.venv/bin/python -m Backend.Memory.worker --provider openrouter_minimax
```

The configured model must exist and support structured output. The initial live smoke test returned HTTP 404 for the current project model, so provider suitability is not yet established. The worker is not enabled by API startup at this stage.

Run tests:

```sh
.venv/bin/python -m unittest discover -s tests -v
```

To enable integration tests, set MEMORY_TEST_DATABASE_URL to an isolated development/test PostgreSQL database. Tests create a unique schema per test, then roll back or drop only that test schema. Without that variable, integration tests are explicitly skipped.

## Integrated chat boundary

Bearer verification supplies the user identity; a legacy request-body user_id is accepted only when it matches. Thread registry and legacy checkpoint ownership are checked before state is returned or used. The debug endpoint is authenticated and owner-scoped. Real OIDC/JWKS configuration still needs deployment verification.

Each chat turn captures its event and a receipt before the graph runs. A PostgreSQL session lock serializes one thread across API processes without a long database transaction. The durable active_message_id survives process crashes. Retries return a cached response or recover the checkpointed turn; they cannot answer a later clarification by accident. This requires direct or session-pooled PostgreSQL connections, not transaction-mode pooling.

Retrieved defaults and their provenance enter the actual analyzer prompt. Explicit trip updates win, and deleting a saved default removes it on the next turn unless the user separately chose that value for this trip. The model must return only the latest user's delta; deterministic tests prove merging, while live model compliance remains an evaluation gate.

The API fails closed on capture/retrieval database failures. Model extraction runs asynchronously and has bounded retries; check the event status before expecting a new preference in another thread. New chat messages cannot overtake an unfinished turn in the same thread.

Chat response receipts and graph checkpoints retain conversation content. Completed receipts discard their retrieval snapshot, but unfinished receipts retain it for recovery. No receipt/checkpoint TTL or full account erasure job is implemented yet. Existing application-wide exception logging also needs a redaction audit before production.

## Incremental delivery roadmap

1. **Storage foundation:** validated records, user-scoped CRUD, migration, tests.
2. **Extraction and write policy:** structured LLM output, durable-versus-trip examples, supported keys, corrections, forgetting, provenance, replay protection, and extraction evaluation cases.
3. **Retrieval and graph integration:** memory loader before analyzer, current-request precedence, authenticated user/thread ownership, persistence of clarification evidence, failure handling, and cross-thread end-to-end tests.
4. **Itinerary quality:** structured itinerary with reasons, budget arithmetic, time/location feasibility, evidence from provider results, and precise treatment of unavailable data.
5. **System design and reliability:** service boundaries, API contracts, deadlines, bounded retries, rate limiting, concurrency, idempotency, data lifecycle, deletion, backups, and database migrations.
6. **Observability and guardrails:** correlated traces across API/graph/tools, latency/token/cost metrics, redacted logs, prompt-injection boundaries, tool validation, and operational alerts.
7. **Evaluation and release gates:** versioned datasets, extraction precision/recall, false-memory writes, preference overrides, cross-user isolation, itinerary correctness, latency/cost budgets, and regression checks in CI.
8. **AWS deployment:** choose compute and managed PostgreSQL after agreeing traffic, budget, region, and availability needs; then infrastructure as code, secrets, private networking, TLS, CI/CD, monitoring, backup/restore exercises, and rollback runbooks.

These are staged deliverables, not a claim that production capabilities already exist. Revisit AWS service choices and documentation when implementing that stage.

## Technical references

- [Psycopg asynchronous connections and cursors](https://www.psycopg.org/psycopg3/docs/advanced/async.html).
- [PostgreSQL INSERT and ON CONFLICT](https://www.postgresql.org/docs/current/sql-insert.html).
