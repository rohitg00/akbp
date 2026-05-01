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
