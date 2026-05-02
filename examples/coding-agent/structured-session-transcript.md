# Structured Coding-Agent Session Transcript

This transcript fixture shows the section shape that `akbp crystallize` can parse without relying on model-specific logs.

## Decisions

- Use the JSONL tool server as the adapter boundary for local coding agents.
- Keep `make validate` as the canonical release gate.

## Preferences

- Prefer dry-run memory writes before applying durable claims.
- Avoid storing raw terminal logs unless the user explicitly asks.

## Blockers

- Blocker: hosted docs cannot use a protocol domain until it serves real schema files.
- Missing: vector search backend is intentionally deferred.

## Action Items

- Update docs/AGENT_FLOW.md after changing the session-end workflow.
- Add adapter examples that cite public-safe file paths only.

## Open Questions

- Should runtime-specific adapters live in this repo or separate packages?
- Which hosted docs path should serve schemas after launch?

## Files Touched

- docs/AGENT_FLOW.md
- adapters/coding-agent-template/session-end.md
- cli/akbp.py
