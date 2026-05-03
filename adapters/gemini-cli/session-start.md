# Gemini CLI Session Start

Use this checklist before planning a repository task.

1. Find `akbp.json` in the repository root or parent directories.
2. Call `akbp.capabilities` and inspect write-review metadata.
3. Call `akbp.context` with the current task.
4. Include only relevant cited claims in the plan.
5. If no AKBP workspace exists, continue normally and do not invent durable memory state.

Example JSONL request:

```json
{"id":"gemini-cli-context","method":"akbp.context","path":".","params":{"task":"implement the next safe CLI-driven change","limit":8}}
```

Follow `docs/AGENT_FLOW.md` for the canonical startup and retrieval loop.
