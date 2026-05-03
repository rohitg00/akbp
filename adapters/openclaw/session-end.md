# OpenClaw Session End

Use this checklist when a session produces durable knowledge.

1. Write a concise local transcript summary with decisions, actions, blockers, preferences, and open questions.
2. Use ingest dry-run for any source file imported during session wrap-up.
3. Preview crystallization with dry-run:

```json
{"id":"openclaw-crystallize-preview","method":"akbp.crystallize_session","path":".","dry_run":true,"params":{"transcript":"session-summary.md","apply":true}}
```

4. Review `review_required`, `apply_instruction`, planned claims, planned sources, and redaction status.
5. Apply only after approval:

```json
{"id":"openclaw-crystallize-approved","method":"akbp.crystallize_session","path":".","approved":true,"params":{"transcript":"session-summary.md","apply":true}}
```

6. Refresh local search after approved writes:

```json
{"id":"openclaw-index-approved","method":"akbp.index","path":".","approved":true,"params":{"incremental":true}}
```

Follow `docs/AGENT_FLOW.md` for the canonical session-end loop.
