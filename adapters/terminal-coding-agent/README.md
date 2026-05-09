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

Use dry-run first unless the user already approved durable memory writes. Prefer transcript-backed crystallization at session end:

```json
{"id":"terminal-crystallize","method":"akbp.crystallize_session","path":".","dry_run":true,"params":{"transcript":"session-summary.md","apply":true}}
```

Use direct claims for small standalone facts:

```json
{"id":"remember-dry-run","method":"akbp.remember","path":".","dry_run":true,"params":{"text":"The repo uses make validate before releases","type":"workflow","evidence":["Makefile"]}}
```

If the dry-run response includes `review_required`, print the planned command and `apply_instruction`. After approval, send the same request with `approved:true` and `dry_run` set to `false` or omitted.

## CLI fallback

```bash
akbp --path . context "current task" --limit 8
akbp --path . remember "The repo uses make smoke before releases" --type workflow --evidence Makefile
```

## Recommended AKBP loop

For substantial tasks, follow `docs/AGENT_FLOW.md`: fetch context first, start source imports with ingest dry-run, use dry-run writes for new durable knowledge, refresh the index after writes, then use `akbp.search` or `akbp.context` before continuing related work.

## Approval-gated write safety

Every adapter must use the same durable write boundary:

- call `akbp.capabilities` before assuming methods or schemas
- call `akbp.context` before planning substantial work
- start source imports with ingest dry-run
- preview session memory with `akbp.session.end` and request-level `dry_run:true`
- surface `review_required` and `apply_instruction` before applying writes
- apply only with request-level `approved:true` after approval or trusted local policy
- Do not store secrets, tokens, cookies, auth headers, private DMs, or raw logs with credentials

Follow `docs/AGENT_FLOW.md` for the complete loop.
