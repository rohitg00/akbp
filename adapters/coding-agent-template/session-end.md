# AKBP Session End

Use this checklist before closing a coding-agent session.

1. Identify durable decisions, preferences, blockers, workflows, and facts.
2. Ignore scratch work, failed guesses, and low-value logs.
3. Add source records for transcript files, commits, or docs when available.
4. Use dry-run first if the session did not explicitly approve writes.
5. Prefer `akbp.crystallize_session` for transcript-backed shutdown memory.
6. Write concise claims with evidence pointers when no transcript exists.

Example transcript dry-run request:

```json
{"id":"crystallize-1","method":"akbp.crystallize_session","path":".","dry_run":true,"params":{"transcript":"session-summary.md","apply":true}}
```

Example direct claim dry-run request:

```json
{"id":"remember-1","method":"akbp.remember","path":".","dry_run":true,"params":{"text":"Safe writes require dry-run before apply","type":"decision","evidence":["session-summary.md"]}}
```

## Write loop

For the full write flow, see `docs/AGENT_FLOW.md`. Prefer source-backed `akbp.ingest` with ingest dry-run preview first, or transcript-backed `akbp.crystallize_session`, then refresh the index with `akbp.index` when the integration does not auto-refresh it.
