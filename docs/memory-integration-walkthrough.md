# Memory integration: code walkthrough

Implemented 2026-09-13. This step connects the existing three-field semantic memory to authenticated chat. Comments in the code explain transaction boundaries, default provenance, interruption replay, and retry IDs.

## Follow one message through the code

1. **Identity — `app/auth.py`, `app/api/travel.py`.** Verify the bearer token and derive a stable user ID. The request cannot select another user's memory. A thread ID selects a conversation, not an account.
2. **Capture — `app/services/travel_service.py`, `Backend/Memory/chat_turns.py`.** Verify thread ownership, acquire a conversation lock, and capture the message. The browser creates one `message_id` and reuses it after timeouts. A short database transaction assigns a per-user sequence and creates a chat receipt.
3. **Retrieve — `Backend/Memory/retrieval.py`.** Load at most three validated preference fields for that user. Save this turn's retrieval snapshot for crash recovery. No model or embedding call is needed for retrieval.
4. **Analyze — `Backend/Graph/nodes/travel_requester.py`.** Refresh old memory defaults, pass the current plan and preferences into the prompt, and merge the model's current-user updates. `memory_applied_defaults` records only fields filled from saved memory; explicit trip choices are preserved independently.
5. **Clarify — `Backend/Graph/nodes/conversation.py`.** Save the assistant's question before entering the interrupt node. The next HTTP message is captured first, then supplied as a resume payload. The node saves that answer as a human message before re-running analysis. It has no database/model side effects before `interrupt`, because that code executes again on resume.
6. **Reply — `record_response`, `finish_turn`.** Save the assistant response in the checkpoint, then save an HTTP receipt and release the unfinished-turn marker. If the HTTP response is lost, retry returns that receipt. If receipt saving failed, retry recovers the checkpointed response.
7. **Learn separately — `Backend/Memory/worker.py`.** Claim a queued message, release the transaction, call the extractor, then validate and persist eligible candidates in a new transaction. Chat does not wait for this worker. The extraction prompt distinguishes general preferences from one-trip requests.

The two orders serve different purposes: a session lock orders chat execution within one thread; the event sequence orders memory changes across every thread belonging to the same user. A slow result from thread A cannot overwrite a newer correction from thread B.

## Default versus explicit choice

Suppose the saved hotel preference is `4_star`:

| Input | Current trip | Saved profile |
|---|---|---|
| New trip, no hotel choice | `4_star` from memory | `4_star` |
| “For this trip, use a 5 star hotel.” | `5_star`, explicit | `4_star` |
| Delete saved hotel preference | Existing explicit `5_star` remains | Empty |
| Continue a different trip that only used the saved default | Old default is removed on the next turn | Empty |

The analyzer's interpretation is still model-dependent. Tests verify the merge and data flow using deterministic analyzer outputs; live delta-quality evaluation remains necessary.

## Local startup

From the project root, apply the migrations to your intended **development** database:

```sh
.venv/bin/python -m Backend.Memory.migrate
```

`DATABASE_URL` comes from your environment or local `.env`. API and worker startup check migration checksums. No migration was applied to the application's configured database during this integration work.

For local token authentication, configure these in your development environment:

```dotenv
APP_ENV=development
TRAVEL_AUTH_MODE=development
TRAVEL_DEV_JWT_SECRET=<a private random secret containing at least 32 bytes>
```

Use the same user UUID each time to keep the same profile. Generate a one-hour development token and paste its output into **Connect account** in the Streamlit sidebar:

```sh
.venv/bin/python -m app.dev_token --user-id 00000000-0000-0000-0000-000000000001
```

Run the following in three separate terminals:

```sh
# API: also available through .venv/bin/python main.py
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```sh
# Independent durable-inbox worker
.venv/bin/python -m Backend.Memory.worker --provider openrouter_minimax
```

```sh
.venv/bin/python -m streamlit run FrontEnd/app.py
```

The provider command uses the existing configuration. The previous live run observed a 404 for its configured model, so update/verify the model configuration before expecting a live demo to succeed. This step did not silently switch providers. The planner also uses configured external travel APIs.

For production, use `TRAVEL_AUTH_MODE=oidc` with `TRAVEL_OIDC_ISSUER`, `TRAVEL_OIDC_AUDIENCE`, and HTTPS `TRAVEL_OIDC_JWKS_URL`. Production browser sign-in, real JWKS verification, and AWS deployment are later work. The current token-entry form is a development interface.

## HTTP contract

`POST /travel/chat`, with `Authorization: Bearer <token>`:

```json
{
  "thread_id": "my-trip-a",
  "message_id": "00000000-0000-0000-0000-000000000010",
  "message": "Help me plan a trip."
}
```

Illustrative clarification response shape; exact wording comes from the model:

```json
{
  "thread_id": "my-trip-a",
  "message_id": "00000000-0000-0000-0000-000000000010",
  "response": "1. Where would you like to go?",
  "interrupted": true,
  "memory_status": "pending"
}
```

A clarification answer uses the **same thread ID and a new message ID**. An HTTP retry uses the **same thread ID, message ID, and text**. Reusing an ID with different content returns 409. Concurrent calls in one thread return 409; retry the original message. A failed turn must be recovered with its original ID before sending a different message in that thread.

Other authenticated endpoints:

| Method | Path | Purpose |
|---|---|---|
| GET | `/travel/me` | Verified account ID |
| GET | `/travel/memories` | Active saved preferences for this account |
| GET | `/travel/memory-events/{message_id}` | `pending`, `processing`, `complete`, `failed`, or `expired` |
| DELETE | `/travel/memories/{memory_key}` | Immediate ordered deletion; requires UUID `Idempotency-Key` header |
| GET | `/travel/debug/state/{thread_id}` | Owner-only checkpoint inspection |

`complete` means extraction finished, including a valid decision to store nothing. A `pending` chat response does not promise that a preference was saved. Refresh the preference view after worker processing. Explicit deletion fences older extraction; it does not erase conversation history or backups.

## Recovery and deployment limits

- The API uses a separate autocommit memory pool so a conversation's session lock cannot exhaust the checkpoint pool. Use direct PostgreSQL or session-mode pooling; transaction-mode pooling cannot preserve session advisory locks correctly.
- Capture/retrieval database failure stops the turn. Extraction failure is asynchronous and retried with bounded backoff. No worker means events stay pending until processed or cleaned up by a later worker poll.
- Legacy completed checkpoints can continue only if their stored owner matches the verified principal. Legacy interrupts inside the old analyzer return 409 with an instruction to start a new chat; they cannot safely resume in the changed graph.
- Completed receipts discard their memory snapshot but retain the response. Unfinished receipts retain their snapshot for recovery. Receipt/checkpoint expiration, full account erasure, application-wide log redaction, and backup retention remain open.
- The new `main.py` starts the authenticated API instead of directly invoking a graph and bypassing capture.

## Verification

Latest local result (2026-09-13): **50 tests passed with no skips** against isolated PostgreSQL 18, including the Streamlit UI tests. Application import and Python compilation also passed.

```sh
# Without a database URL, database cases are explicitly skipped.
.venv/bin/python -m unittest discover -s tests -v

# Set MEMORY_TEST_DATABASE_URL to an isolated PostgreSQL test database first.
# Tests create random schemas and remove or roll back only those schemas.
MEMORY_TEST_DATABASE_URL='<test connection string>' .venv/bin/python -m unittest discover -s tests -v
```

`tests/test_memory_chat_integration.py` uses real PostgreSQL, the production graph edges, real capture/retrieval/worker/persistence, and deterministic model boundaries. It checks cross-thread memory, current-trip overrides, deletion, checkpoint recovery, interruption retries, HTTP authentication, and isolation. `tests/test_memory_frontend.py` exercises the Streamlit account, message retry, and deletion controls with a mocked HTTP client. These are integration regressions, not live LLM quality or travel-data evaluations.
