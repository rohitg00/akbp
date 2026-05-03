# Coding Agent Adapter Template

This adapter template shows how a coding agent can use AKBP without inventing a private memory format.

Use it when an agent can read project instructions, run local commands, or communicate with the AKBP JSONL tool server.

## Files

- `instructions.md`: instruction block to copy into an agent runtime.
- `config.example.json`: local tool-server configuration example.
- `session-start.md`: startup checklist for retrieving relevant context.
- `session-end.md`: end-of-session checklist for crystallizing durable knowledge.
- `privacy.md`: safety defaults for secrets, scopes, and write approval.

## Contract

Adapters may translate runtime-specific events into AKBP calls, but durable knowledge remains in AKBP artifacts:

- `akbp.json`
- `claims/claims.jsonl`
- `wiki/`
- `graph/`
- `raw/sources/`
- `.akbp/audit.log.jsonl`

## Recommended flow

Use `docs/AGENT_FLOW.md` as the default loop for runtime integrations: preview source imports with ingest dry-run, inspect `review_required` and `apply_instruction` from dry-run responses, apply approved imports, retrieve with search/context, run `akbp.crystallize_session` for transcript-backed session memory with dry-run preview, refresh the index, and cite claims when prior knowledge affects work.

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
