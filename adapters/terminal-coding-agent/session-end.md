# Terminal Coding Agent Session End

Before ending the session:

1. Summarize durable changes.
2. Record decisions, workflows, blockers, and preferences that will matter later.
3. Attach evidence such as commit hashes, file paths, or docs.
4. Use dry-run first if write approval is unclear.

Example:

```json
{"id":"decision","method":"akbp.remember","path":".","dry_run":true,"params":{"text":"Release validation requires guard, tests, smoke, and install smoke","type":"workflow","evidence":["Makefile"]}}
```
