# OpenClaw Session Start

Use this checklist before planning a task.

1. Find `akbp.json` in the active workspace or parent directories.
2. Call `akbp.capabilities` and inspect method metadata.
3. Call `akbp.context` with the current user request and a small limit.
4. Include relevant cited claims in the task plan only when they affect the work.
5. If no AKBP workspace exists, continue normally and do not invent durable memory state.

Example JSONL request:

```json
{"id":"openclaw-context","method":"akbp.context","path":".","params":{"task":"summarize the current implementation blocker","limit":8}}
```

Follow `docs/AGENT_FLOW.md` for the canonical startup and retrieval loop.
