# Adapter lifecycle session summary

## Task
Prepare a release candidate without losing project decisions between agent sessions.

## Durable decisions
- Use `akbp.session.start` at startup to retrieve relevant claims before planning.
- Use `akbp.session.end` with `dry_run:true` before any durable shutdown write.
- Only repeat shutdown apply with `approved:true` after reviewing the summary, planned page, evidence, and skipped claims.

## Evidence
- docs/TOOL_CONTRACT.md
- adapters/coding-agent-template/config.example.json

## Next steps
- Refresh the index after approved lifecycle writes.
- Cite retrieved claims when prior AKBP context affects future work.
