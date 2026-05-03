# Claude Code Adapter

This adapter shows how a repository coding agent can use AKBP for durable project knowledge while keeping repository instructions and AKBP separate.

Use it when the agent can read instruction files, run local commands, or call the AKBP JSONL tool server.

## Startup flow

1. Discover `akbp.json` in the repository root or parent directories.
2. Call `akbp.capabilities` before assuming method names, schemas, or write behavior.
3. Call `akbp.context` with the current task before planning.
4. Cite retrieved claims when they affect code changes, release decisions, or user-facing recommendations.

## Write flow

Start durable writes with dry-run. Render `review_required` and `apply_instruction` before applying.

```json
{"id":"claude-code-crystallize-preview","method":"akbp.crystallize_session","path":".","dry_run":true,"params":{"transcript":"session-summary.md","apply":true}}
```

Apply only after approval or trusted local policy:

```json
{"id":"claude-code-crystallize-approved","method":"akbp.crystallize_session","path":".","approved":true,"params":{"transcript":"session-summary.md","apply":true}}
```

For imported notes or repo artifacts, begin with ingest dry-run:

```json
{"id":"claude-code-ingest-preview","method":"akbp.ingest","path":".","dry_run":true,"params":{"file":"docs/review-note.md","title":"Review note","claim":"The repository validates releases with make validate.","claim_type":"workflow"}}
```

## Instruction-file integration

Add the relevant parts of `instructions.md`, `session-start.md`, and `session-end.md` to the repository instruction file used by the runtime. Keep durable records in AKBP artifacts, not in private runtime-only notes.

Follow `docs/AGENT_FLOW.md`: retrieve context first, preview source imports, crystallize session knowledge with dry-run preview before apply, refresh the index after approved writes, and cite claims when prior knowledge affects work.
