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
./examples/rich-context-artifact/run.sh
```

Expected behavior:

- `import-check` accepts one source and two claims.
- `import-apply --dry-run` previews the objects that would be written.
- `import-apply --approved` writes only after explicit approval.
- `source verify` confirms the reviewed source hash.
- `context --require-citations` recalls the applied claims with citations.
- `export-check --fail-on-issues` verifies the portable bundle.

## Pattern

Use this pattern for:

- agent handoffs
- release readiness reviews
- decision review pages
- research maps
- postmortem summaries

Keep the rule simple: generated artifacts help humans review knowledge; AKBP JSONL remains the durable protocol boundary.
