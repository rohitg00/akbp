# Example Coding Agent Session End

Use this shutdown routine after substantial work.

1. Summarize durable decisions, workflows, blockers, preferences, and changed files.
2. Propose memory writes with citations.
3. Use dry-run for write-capable requests unless approval already exists.
4. Refresh the search index when durable writes were applied.
5. Keep transient logs and secrets out of AKBP.

Example dry-run write:

```json
{"id":"remember-end","method":"akbp.remember","path":".","dry_run":true,"params":{"text":"Release validation uses make smoke","type":"workflow","evidence":["Makefile"]}}
```
