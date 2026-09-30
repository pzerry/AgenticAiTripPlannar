# Memory implementation acceptance checklist

Source: Design Long Term Memory (ChatGPT conversation 6aa23104-e1d8-83e8-91d2-c718c171acaa), reviewed 2026-09-11 against the working tree.

The goal is the full usable memory architecture, not only the initial preference table. Check an item only after recording direct evidence. This document is a working checklist, not a release certification.

- [x] Read the linked discussion and inspect current source, including contracts.py and policy.py.
- [ ] Compare Mem0 with a controlled extractor using the six synthetic acceptance scenarios; record versions, correctness, latency, processing/deletion behavior, and measured usage. Do not call mocked model results a live evaluation.
- [ ] Record the architecture decision, ownership boundaries, memory types, and tradeoffs.
- [x] Authenticate user identity independently of request-body IDs; enforce thread ownership before checkpoint access, including debug and resume routes.
- [x] Capture stable message IDs, server ordering, and clarification answers; preserve complete planner conversation history.
- [ ] Extract only explicit self-attributed durable preferences with verifiable evidence; abstain on ambiguity and untrusted tool/assistant text.
- [x] Apply policy before persistence; deterministic duplicate handling, revision ordering, concurrency tests, and retry protection.
- [x] Explicit forgetting removes active data and fences delayed/replayed writes; document source/checkpoint retention separately.
- [x] Durable queued extraction with leases, timeout, bounded retries, restart recovery, and terminal failure handling.
- [x] Relevant bounded retrieval into the actual analyzer prompt; current-trip choices override saved defaults without changing the durable profile.
- [x] End-to-end acceptance: learn in thread A, retrieve in B, allow a trip exception, correct the profile, forget, retry old work, and isolate user B.
- [x] User memory inspect/delete controls through authenticated API and usable frontend.
- [ ] Structured redacted telemetry: outcome/rejection/conflict counts, selected IDs, latency, usage, failures; no memory text in routine logs.
- [ ] Evaluation dataset and executable regression gates covering admission, attribution, evidence, ordering, deletion, isolation, and planner application.
- [ ] Versioned migrations and runnable deployment/worker setup; local verification and explicit remaining AWS prerequisites.
- [ ] Document file roles, lifecycle, operational commands, failure behavior, retention, and AWS deployment design.

## Current evidence — 2026-09-13

The checked items are supported by deterministic tests, including real PostgreSQL and the actual LangGraph edges. They do not certify LLM classification quality, real OIDC deployment, or live travel-provider results.

Final combined verification: **50 tests passed, no skips**, using isolated PostgreSQL 18 schemas on 2026-09-13. Python compilation, API import, and whitespace checks for the touched application paths also passed.

- JWT authentication is installed on chat, debug, preference, and event-status routes. Signed development tokens and cross-user rejection are tested. Production OIDC/JWKS remains to verify.
- Message capture, response receipts, per-thread process coordination, interruption recovery, and assistant/human history are connected. Old HTTP retries cannot answer later clarification questions.
- Retrieval feeds the analyzer prompt and tracks default provenance. Trip exceptions preserve the saved profile; deletion refreshes memory-derived defaults on subsequent turns.
- Explicit deletion uses per-user ordering and fences pending older work. Repeating an old deletion does not erase a subsequently learned preference.
- Streamlit requires a verified account token, preserves retry IDs after timeouts, supports preference inspection/deletion, and clears local conversations when switching users.
- Migrations 001–003 were applied only to isolated test schemas. The configured application database remains unmigrated.
- The corrected Mem0 probe completed; see memory-backend-decision.md. Controlled extraction has one successful live JSON-mode smoke case; the complete live suite remains unresolved.

## Next milestone

Complete live extraction and planner-delta evaluation with an available, reliable configured model. The previously configured free model returned 404 in the earlier run; no new live availability claim is made.

Then finish richer preference/episode design, redacted application telemetry, receipt/checkpoint retention and full erasure, operational failure handling, and AWS deployment. Three structured preference fields do not cover the whole memory architecture.

See [the code walkthrough](memory-integration-walkthrough.md) for file roles, startup, request shape, and verification commands.
