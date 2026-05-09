# Example Coding Agent Adapter

This fixture shows the minimum complete adapter shape for a generic coding-agent runtime.

It is intentionally runtime-neutral. Copy it when starting a new adapter, then replace the generic command names and UI notes with the target runtime's public setup details.

## Startup flow

1. Locate `akbp.json` in the repository root or a parent directory.
2. Start or connect to the local JSONL tool server.
3. Call `akbp.capabilities` before assuming methods exist.
4. Call `akbp.context` with the current task before planning substantial work.
5. Cite retrieved claims when they affect decisions.

## Write flow

Use dry-run first. Prefer transcript-backed crystallization when a session summary exists:

```json
{"id":"example-crystallize","method":"akbp.crystallize_session","path":".","dry_run":true,"params":{"transcript":"session-summary.md","apply":true}}
```

Use direct claims when there is no transcript or summary to crystallize:

```json
{"id":"example-write","method":"akbp.remember","path":".","dry_run":true,"params":{"text":"The project validates releases with make validate","type":"workflow","evidence":["Makefile"]}}
```

Apply only after review or explicit approval. If the response includes `review_required`, surface `apply_instruction` before sending the non-dry-run request with `approved:true`.

## Recommended AKBP loop

Follow `docs/AGENT_FLOW.md`: retrieve context first, perform work, propose cited durable writes, refresh the index when useful, and retrieve again before continuing related work.

## Approval-gated write safety

Every adapter must use the same durable write boundary:

- call `akbp.capabilities` before assuming methods or schemas
- call `akbp.context` before planning substantial work
- start source imports with ingest dry-run
- validate JSONL exports with `akbp.import_check` and preview accepted imports with `akbp.import_apply` plus `dry_run:true`
- preview session memory with `akbp.session.end` and request-level `dry_run:true`
- surface `review_required` and `apply_instruction` before applying writes
- apply only with request-level `approved:true` after approval or trusted local policy
- Do not store secrets, tokens, cookies, auth headers, private DMs, or raw logs with credentials

Follow `docs/AGENT_FLOW.md` for the complete loop.
