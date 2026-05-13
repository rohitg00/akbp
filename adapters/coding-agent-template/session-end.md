# AKBP Session End

Use this checklist before closing a coding-agent session.

1. Identify durable decisions, preferences, blockers, workflows, and facts.
2. Ignore scratch work, failed guesses, and low-value logs.
3. Add source records for transcript files, commits, or docs when available.
4. Use request-level `dry_run:true` before every write-capable session-end operation.
5. Prefer `akbp.session.end` for adapter lifecycle shutdown memory. It uses the same transcript crystallization contract as `akbp.crystallize_session` but gives integrations a stable lifecycle method name.
6. Apply only after review by repeating the same method/path/params with request-level `approved:true` and without `dry_run:true`.
7. Write concise claims with evidence pointers when no transcript exists.

Example transcript dry-run request:

```json
{"id":"session-end-1","method":"akbp.session.end","path":".","dry_run":true,"params":{"transcript":"session-summary.md","apply":true}}
```

Example approved transcript apply request:

```json
{"id":"session-end-apply-1","method":"akbp.session.end","path":".","approved":true,"params":{"transcript":"session-summary.md","apply":true}}
```

Example direct claim dry-run request:

```json
{"id":"remember-1","method":"akbp.remember","path":".","dry_run":true,"params":{"text":"Safe writes require dry-run before apply","type":"decision","evidence":["session-summary.md"]}}
```

Example approved direct claim apply request:

```json
{"id":"remember-apply-1","method":"akbp.remember","path":".","approved":true,"params":{"text":"Safe writes require dry-run before apply","type":"decision","evidence":["session-summary.md"]}}
```

## Write loop

For the full write flow, see `docs/AGENT_FLOW.md`. Prefer source-backed `akbp.ingest` with ingest dry-run preview first, transcript-backed `akbp.session.end`, or `akbp.import_check` plus `akbp.import_apply` for reviewed JSONL exports. Refresh the index with `akbp.index` when the integration does not auto-refresh it.
