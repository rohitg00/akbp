# Terminal Coding Agent Adapter

This adapter is for command-line coding agents that can run local commands and read repository files.

It uses the AKBP JSONL tool server when available and falls back to the AKBP CLI when the server is not configured.

## Startup flow

1. Find `akbp.json` in the current repo or parent directories.
2. Start the local tool server with `akbp-tool-server`, or use `akbp` commands directly.
3. Call `akbp.capabilities` to discover methods and schemas.
4. Call `akbp.context` with the current task before planning.
5. Cite retrieved claims when they affect code or decisions.

## Write flow

Use dry-run first unless the user already approved durable memory writes.

```json
{"id":"remember-dry-run","method":"akbp.remember","path":".","dry_run":true,"params":{"text":"The repo uses make smoke before releases","type":"workflow","evidence":["Makefile"]}}
```

After approval, send the same request with `dry_run` set to `false` or omitted.

## CLI fallback

```bash
akbp --path . context "current task" --limit 8
akbp --path . remember "The repo uses make smoke before releases" --type workflow --evidence Makefile
```
