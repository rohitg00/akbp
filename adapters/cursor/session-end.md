# Cursor Session End

Use this checklist when workspace edits create durable knowledge.

1. Write a concise local transcript summary with decisions, actions, blockers, preferences, and open questions.
2. Use ingest dry-run for imported source notes, specs, or review artifacts.
3. Preview crystallization with dry-run:

```json
{"id":"cursor-crystallize-preview","method":"akbp.crystallize_session","path":".","dry_run":true,"params":{"transcript":"session-summary.md","apply":true}}
```

4. Review planned claims, planned sources, redaction status, `review_required`, and `apply_instruction`.
5. Apply only after approval:

```json
{"id":"cursor-crystallize-approved","method":"akbp.crystallize_session","path":".","approved":true,"params":{"transcript":"session-summary.md","apply":true}}
```

6. Refresh local search after approved writes:

```json
{"id":"cursor-index-approved","method":"akbp.index","path":".","approved":true,"params":{"incremental":true}}
```

Follow `docs/AGENT_FLOW.md` for the canonical session-end loop.
