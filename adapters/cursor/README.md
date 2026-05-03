# Cursor Adapter

This adapter shows how an editor-based coding agent can use AKBP for durable project knowledge without replacing editor rules or repository instructions.

Use it when the agent can read workspace files, run local commands, or call the AKBP JSONL tool server.

## Startup flow

1. Discover `akbp.json` in the workspace root or parent directories.
2. Call `akbp.capabilities` before assuming method names, schemas, or write behavior.
3. Call `akbp.context` with the current task before planning edits.
4. Cite retrieved claims when they affect code changes, release decisions, or user-facing recommendations.

## Write flow

Start durable writes with dry-run. Render `review_required` and `apply_instruction` before applying.

```json
{"id":"cursor-crystallize-preview","method":"akbp.crystallize_session","path":".","dry_run":true,"params":{"transcript":"session-summary.md","apply":true}}
```

Apply only after approval or trusted local policy:

```json
{"id":"cursor-crystallize-approved","method":"akbp.crystallize_session","path":".","approved":true,"params":{"transcript":"session-summary.md","apply":true}}
```

For imported notes, specs, or review artifacts, begin with ingest dry-run:

```json
{"id":"cursor-ingest-preview","method":"akbp.ingest","path":".","dry_run":true,"params":{"file":"docs/spec-note.md","title":"Spec note","claim":"The workspace validates releases with make validate.","claim_type":"workflow"}}
```

## Editor rule integration

Copy the relevant parts of `instructions.md`, `session-start.md`, and `session-end.md` into editor rules or project instructions. Keep durable records in AKBP artifacts, not private editor-only storage.

Follow `docs/AGENT_FLOW.md`: retrieve context first, preview source imports, crystallize session knowledge with dry-run preview before apply, refresh the index after approved writes, and cite claims when prior knowledge affects work.

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
