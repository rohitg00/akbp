# Existing memory migration

This example shows the safest path for moving useful facts out of an existing agent memory store, notes folder, or tool export into AKBP.

The goal is not to trust another memory system blindly. The goal is to convert reviewed source and claim records into portable AKBP artifacts, preview the write, apply only after approval, then prove later recall works with citations.

## Run

From the repository root:

```bash
examples/existing-memory-migration/run.sh
```

Expected success marker:

```text
AKBP existing memory migration example passed
```

## Migration shape

A small migration export should contain line-oriented JSON records:

```json
{"kind":"source","id":"source_existing_memory_note","type":"note","locator":"memory-export/session-policy.md","title":"Existing memory session policy"}
{"kind":"claim","id":"claim_existing_memory_session_policy","text":"Project memory updates must be reviewed at session boundaries.","type":"policy","status":"working","confidence":0.82,"evidence":["source_existing_memory_note"],"scope":"project"}
```

Before applying it:

1. Run `akbp import-check incoming.jsonl --fail-on-rejected`.
2. Run `akbp import-apply incoming.jsonl --dry-run`.
3. Review accepted ids, rejected ids, planned source ids, and planned claim ids.
4. Apply with `akbp import-apply incoming.jsonl --approved`.
5. Rebuild the index and query context for the next agent session.

## Reject instead of importing

Stop the migration when the export has:

- malformed JSONL
- secret-like values
- unsupported object kinds
- claims that cite missing `source_...` evidence ids
- broad summaries that should be split into smaller reviewed claims

AKBP treats migration as a review gate, not a bulk memory dump. Existing memory can be useful input, but durable AKBP knowledge should remain cited, inspectable, and portable.
