# Editor Coding Agent Adapter

This adapter is for coding agents embedded in editors or IDE-like environments.

The adapter keeps AKBP as the durable knowledge format while letting the editor agent use local project files, commands, and tool calls.

## Startup flow

1. Read `akbp.json` when opening a project.
2. Discover capabilities from the local JSONL tool server.
3. Fetch task-specific context before making multi-file edits.
4. Show citations when prior knowledge affects the proposed change.

## Write flow

Editor agents should not silently write durable memory. Use dry-run for proposed writes and ask for approval before applying them.

```json
{"id":"pref-dry-run","method":"akbp.remember","path":".","dry_run":true,"params":{"text":"Prefer small verified commits over large unvalidated changes","type":"preference","evidence":["session-summary.md"]}}
```

## UI guidance

Show memory writes as a reviewable diff-like list:

- claim text
- claim type
- evidence
- scope
- whether it supersedes an older claim

## Recommended AKBP loop

Editor agents should follow `docs/AGENT_FLOW.md` while keeping writes reviewable in the UI: ingest or cite source material, propose evidence-backed claims, refresh the index, and surface citations beside retrieved context.
