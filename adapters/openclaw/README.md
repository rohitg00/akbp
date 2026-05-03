# OpenClaw Adapter

This adapter shows how an OpenClaw workspace can use AKBP as durable project knowledge without turning chat history into the source of truth.

Use it when an OpenClaw agent can read workspace instructions, run local CLI commands, or call a local JSONL tool server.

## Startup flow

1. Discover `akbp.json` in the active workspace or a parent directory.
2. Call `akbp.capabilities` to learn supported methods, schemas, and write-review requirements.
3. Call `akbp.context` with the current user task before planning.
4. Cite retrieved claims when they affect actions, repo changes, or user-facing recommendations.

## Write flow

Start durable writes with dry-run. Render `review_required` and `apply_instruction` to the user or local runtime before applying.

```json
{"id":"openclaw-crystallize-preview","method":"akbp.crystallize_session","path":".","dry_run":true,"params":{"transcript":"session-summary.md","apply":true}}
```

Apply only after explicit approval or trusted local policy:

```json
{"id":"openclaw-crystallize-approved","method":"akbp.crystallize_session","path":".","approved":true,"params":{"transcript":"session-summary.md","apply":true}}
```

For source imports, begin with ingest dry-run:

```json
{"id":"openclaw-ingest-preview","method":"akbp.ingest","path":".","dry_run":true,"params":{"file":"docs/decision-note.md","title":"Decision note","claim":"The project validates releases with make validate.","claim_type":"workflow"}}
```

## Recommended loop

Follow `docs/AGENT_FLOW.md`: fetch context first, keep writes cited, preview source imports, crystallize session knowledge with dry-run preview before apply, refresh the index after approved writes, and query again before related follow-up work.

## Approval-gated write safety

Every adapter must use the same durable write boundary:

- call `akbp.capabilities` before assuming methods or schemas
- call `akbp.context` before planning substantial work
- start source imports with ingest dry-run
- preview session memory with `akbp.crystallize_session` and request-level `dry_run:true`
- surface `review_required` and `apply_instruction` before applying writes
- apply only with request-level `approved:true` after approval or trusted local policy
- Do not store secrets, tokens, cookies, auth headers, private DMs, or raw logs with credentials

Follow `docs/AGENT_FLOW.md` for the complete loop.
