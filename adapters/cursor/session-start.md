# Cursor Session Start

Use this checklist before planning workspace edits.

1. Find `akbp.json` in the workspace root or parent directories.
2. Call `akbp.capabilities` and inspect write-review metadata.
3. Call `akbp.context` with the current task.
4. Include only relevant cited claims in the plan.
5. If no AKBP workspace exists, continue normally and do not invent durable memory state.

Example JSONL request:

```json
{"id":"cursor-context","method":"akbp.context","path":".","params":{"task":"implement the next safe editor change","limit":8}}
```

Follow `docs/AGENT_FLOW.md` for the canonical startup and retrieval loop.
