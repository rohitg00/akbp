# Terminal Coding Agent Session End

Before ending the session:

1. Summarize durable changes.
2. Record decisions, workflows, blockers, and preferences that will matter later.
3. Attach evidence such as commit hashes, file paths, docs, or a session summary.
4. Use dry-run first if write approval is unclear.
5. Prefer `akbp.crystallize_session` when a transcript or session summary exists.
6. For JSONL exports, run `akbp.import_check`, then preview `akbp.import_apply` with `dry_run:true`.

Example transcript dry-run:

```json
{"id":"crystallize-terminal","method":"akbp.session.end","path":".","dry_run":true,"params":{"transcript":"session-summary.md","apply":true}}
```

Example direct claim dry-run:

```json
{"id":"decision","method":"akbp.remember","path":".","dry_run":true,"params":{"text":"Release validation requires make validate","type":"workflow","evidence":["Makefile"]}}
```
