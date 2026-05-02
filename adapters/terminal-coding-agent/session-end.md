# Terminal Coding Agent Session End

Before ending the session:

1. Summarize durable changes.
2. Record decisions, workflows, blockers, and preferences that will matter later.
3. Attach evidence such as commit hashes, file paths, docs, or a session summary.
4. Use dry-run first if write approval is unclear.
5. Prefer `akbp.crystallize_session` when a transcript or session summary exists.

Example transcript dry-run:

```json
{"id":"crystallize-terminal","method":"akbp.crystallize_session","path":".","dry_run":true,"params":{"transcript":"session-summary.md","apply":true}}
```

Example direct claim dry-run:

```json
{"id":"decision","method":"akbp.remember","path":".","dry_run":true,"params":{"text":"Release validation requires make validate","type":"workflow","evidence":["Makefile"]}}
```
