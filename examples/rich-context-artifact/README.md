# Rich context artifact example

This example shows AKBP as the source of truth and a static HTML file as the review surface.

The HTML is intentionally not the write path. It is a navigable human artifact generated from portable AKBP objects. Durable writes still use JSONL proposals, validation, dry-run review, and explicit approval.

## Files

| File | Purpose |
|------|---------|
| `source-note.md` | Reviewed source material for the example claims |
| `updates.jsonl` | Proposed AKBP source and claim records |
| `agent-handoff.html` | Static review page that presents the proposed knowledge |

## Try the write gate

From the repository root:

```bash
TMP=$(mktemp -d)
python3 cli/akbp.py --path "$TMP/kb" init
python3 cli/akbp.py --path "$TMP/kb" import-check examples/rich-context-artifact/updates.jsonl --fail-on-rejected
python3 cli/akbp.py --path "$TMP/kb" import-apply examples/rich-context-artifact/updates.jsonl --dry-run
python3 cli/akbp.py --path "$TMP/kb" import-apply examples/rich-context-artifact/updates.jsonl --approved
```

Expected behavior:

- `import-check` accepts one source and two claims.
- `import-apply --dry-run` previews the objects that would be written.
- `import-apply --approved` writes only after explicit approval.

## Pattern

Use this pattern for:

- agent handoffs
- release readiness reviews
- decision review pages
- research maps
- postmortem summaries

Keep the rule simple: generated artifacts help humans review knowledge; AKBP JSONL remains the durable protocol boundary.
