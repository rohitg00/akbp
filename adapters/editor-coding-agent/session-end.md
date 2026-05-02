# Editor Coding Agent Session End

When a user accepts changes:

1. Identify durable knowledge created during the edit.
2. Create dry-run memory proposals.
3. Prefer `akbp.crystallize_session` for accepted session summaries.
4. Ask the user to approve or reject the proposals.
5. Apply approved writes only.

Example transcript dry-run:

```json
{"id":"crystallize-editor","method":"akbp.crystallize_session","path":".","dry_run":true,"params":{"transcript":"session-summary.md","apply":true}}
```

Avoid storing raw editor buffers unless the user explicitly requests it.
