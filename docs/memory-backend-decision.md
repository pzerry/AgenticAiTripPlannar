# Memory backend decision — 2026-09-11

## Decision

Use the application's PostgreSQL records and revision boundary as the authority for the three supported structured travel preferences. Keep extraction replaceable and outside the write transaction. Do not automatically write user conversations into Mem0 in the application.

This decision is about the structured profile. Richer preferences (quiet hotels near transit, for example) and attributed trip experiences require an additional schema/retrieval decision; they are not represented by the current three keys. Procedural rules remain version-controlled code and prompts. Live prices and availability remain provider data with freshness requirements, not durable user memory.

## Evidence

The comparison used the installed **Mem0 OSS 2.0.20**, with local Qdrant and SQLite in a temporary directory, telemetry disabled, the configured OpenRouter analyzer model, and an OpenRouter embedding endpoint. Only synthetic travel messages were sent. The project database was not involved.

The valid run is recorded in `evals/memory/mem0-probe-corrected.json`; the script is `evals/memory/compare_mem0.py`.

| Scenario | Observed Mem0 behavior in the corrected run |
|---|---|
| Durable nonstop preference | Stored a preference. |
| Trip-only exception | Returned no new memory. |
| General correction to allow connections | Added a correction while retaining the older preference. |
| Partner preference | Returned no new memory. |
| Natural-language forgetting | Returned no new memory; subsequent get_all still returned both flight memories. |
| Different-user search | Returned no memories. |
| Explicit delete_all API | Removed the synthetic user's active memories; get_all returned empty. |

The initial probe used invalid top-level retrieval arguments and a smaller output limit. Its retrieval errors are defects in that probe, not evidence of Mem0 isolation failure. Do not use that run as the final comparison. The corrected probe uses filters as required by the installed version.

These observations support requiring application-controlled correction and forgetting semantics. They do not establish that Mem0 is generally inaccurate. They also do not establish that its explicit deletion API erases every possible source/history store; that was not audited in this probe.

Observed processing time ranged from about 15 seconds to 234 seconds per add in the corrected run. This is one small run on a free model endpoint, not a production latency benchmark. LLM usage and provider-reported costs are recorded, but embedding cost was not measured. No total-cost claim is justified.

## Controlled pipeline validation

The PostgreSQL tests verify stable IDs, per-user ordering, concurrent capture/claims, stale-write rejection, forgetting fences, lease recovery, retries, and source scrubbing. The policy tests use constructed candidates; they do not prove the model classifies natural language correctly.

The first JSON-mode live extraction smoke test passed, taking approximately 39 seconds. Other attempts returned HTTP 404, HTTP 429, or exceeded the timeout. The full live evaluation remains a release gate. Its results must not be replaced by mocked results or summarized as passing until all cases are checked.

## Operational implications

- One authoritative profile avoids conflicting copies across PostgreSQL and a separate memory engine.
- Exact retrieval of three bounded fields requires no vector service or embedding request.
- The event inbox is durable before extraction, so model failure does not require losing the user's message.
- Claims and model calls use separate transaction boundaries. Leases and source sequence checks handle crashed and delayed work.
- Worker output must pass evidence and eligibility checks before writing. Confidence is not authorization.
- Identity verification and thread ownership were connected on 2026-09-13 and tested through authenticated HTTP routes. Real production OIDC configuration remains to verify.

## Sources

- [Mem0 deployment comparison](https://docs.mem0.ai/platform/platform-vs-oss)
- [Mem0 OSS overview](https://docs.mem0.ai/open-source/overview)
- Installed 2.0.20 source inspected for `Memory.add`, `get_all`, `search`, and the additive extraction pipeline.
- [LangGraph memory concepts](https://docs.langchain.com/oss/python/concepts/memory)
- [PostgreSQL locking](https://www.postgresql.org/docs/current/explicit-locking.html)
