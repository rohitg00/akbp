# Editor Coding Agent Session End

When a user accepts changes:

1. Identify durable knowledge created during the edit.
2. Create dry-run memory proposals.
3. Prefer `akbp.crystallize_session` for accepted session summaries.
4. For JSONL exports, run `akbp.import_check`, then preview `akbp.import_apply` with `dry_run:true`.
5. Ask the user to approve or reject the proposals.
6. Apply approved writes only with request-level `approved:true`.

Example transcript dry-run:

```json
{"id":"crystallize-editor","method":"akbp.crystallize_session","path":".","dry_run":true,"params":{"transcript":"session-summary.md","apply":true}}
```

Avoid storing raw editor buffers unless the user explicitly requests it.
