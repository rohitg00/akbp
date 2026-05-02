# Example Coding Agent Session End

Use this shutdown routine after substantial work.

1. Summarize durable decisions, workflows, blockers, preferences, and changed files.
2. Propose transcript-backed memory writes with citations.
3. Use dry-run for write-capable requests unless approval already exists.
4. Refresh the search index when durable writes were applied.
5. Keep transient logs and secrets out of AKBP.

Example transcript dry-run write:

```json
{"id":"crystallize-end","method":"akbp.crystallize_session","path":".","dry_run":true,"params":{"transcript":"session-summary.md","apply":true}}
```

Example direct claim dry-run write:

```json
{"id":"remember-end","method":"akbp.remember","path":".","dry_run":true,"params":{"text":"Release validation uses make validate","type":"workflow","evidence":["Makefile"]}}
```
