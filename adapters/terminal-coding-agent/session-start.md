# Terminal Coding Agent Session Start

Run this sequence at the beginning of substantial work.

```json
{"id":"caps","method":"akbp.capabilities","path":"."}
```

Then request context for the task:

```json
{"id":"ctx","method":"akbp.context","path":".","params":{"task":"describe the coding task here","limit":8}}
```

Use the result to identify known workflows, preferences, blockers, and relevant prior decisions.
