# Example Coding Agent Session Start

Use this startup routine for substantial work.

1. Locate the AKBP root by finding `akbp.json`.
2. Read `akbp.json` and `AKBP.md`.
3. Discover local tool-server capabilities.
4. Request context for the current task.
5. Include relevant cited claims in the plan.

Example request:

```json
{"id":"context-start","method":"akbp.context","path":".","params":{"task":"current task","limit":8}}
```
