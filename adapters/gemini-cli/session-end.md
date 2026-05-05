# Gemini CLI Session End

Use this checklist when a CLI-driven task creates durable knowledge.

1. Write a concise local transcript summary with decisions, actions, blockers, preferences, and open questions.
2. Use ingest dry-run for imported source notes, specs, command summaries, or review artifacts.
3. Preview crystallization with dry-run:

```json
{"id":"gemini-cli-crystallize-preview","method":"akbp.crystallize_session","path":".","dry_run":true,"params":{"transcript":"session-summary.md","apply":true}}
```

4. For JSONL exports, run `akbp.import_check`, then preview `akbp.import_apply` with `dry_run:true`.
5. Review planned claims, planned sources, import `would_write` ids, redaction status, `review_required`, and `apply_instruction`.
6. Apply only after approval:

```json
{"id":"gemini-cli-crystallize-approved","method":"akbp.crystallize_session","path":".","approved":true,"params":{"transcript":"session-summary.md","apply":true}}
```

7. Refresh local search after approved writes:

```json
{"id":"gemini-cli-index-approved","method":"akbp.index","path":".","approved":true,"params":{"incremental":true}}
```

Follow `docs/AGENT_FLOW.md` for the canonical session-end loop.
