# Existing memory migration

This example shows the safest path for moving useful facts out of an existing
agent memory store, hosted coding-agent memory, notes folder, or tool export
into AKBP.

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

`import-check` and `import-apply --dry-run` include a `review` section for
adapter UIs and CI logs. Treat `review.ready_for_reviewed_apply:true` as the
minimum green light before presenting an approval button. If
`claims_without_evidence` is non-empty, the import may still be syntactically
valid, but it has not met AKBP's trust bar for durable project memory.

## Reject instead of importing

Stop the migration when the export has:

- malformed JSONL
- secret-like values
- unsupported object kinds
- claims that cite missing `source_...` evidence ids
- broad summaries that should be split into smaller reviewed claims

AKBP treats migration as a review gate, not a bulk memory dump. Existing memory can be useful input, but durable AKBP knowledge should remain cited, inspectable, and portable.

## Hosted or opaque memory exports

Hosted coding-agent memory and tool memory servers are useful as runtime
context, but their exports often arrive as uncited summaries, cache records, or
broad session notes. Treat those as runtime scratch until they have been
promoted into AKBP records with source evidence.

Use this promotion rule:

- import source-backed project decisions, workflow constraints, and lifecycle
  records
- keep runtime scratchpads, uncited summaries, bridge cache metadata, and
  private logs out of AKBP
- require `review.ready_for_reviewed_apply:true` before any approval UI offers
  `import-apply --approved`
- if `claims_without_evidence` or `claims_without_source_evidence` is
  non-empty, send the export back for source review instead of applying it

The runnable example includes an opaque-host export that parses cleanly but does
not pass the reviewed-apply gate because the claim has no source evidence.
