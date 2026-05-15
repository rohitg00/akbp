# GitHub Copilot Adapter

This adapter shows how a GitHub Copilot workspace can use AKBP as reviewable project knowledge instead of relying only on product-local memory or chat history.

Use it when Copilot can read repository files and the developer can run local terminal commands from the checkout.

## Cloud agent tool safety

GitHub Copilot cloud agent can be connected to repository tools, but hosted-agent tool calls may run without an interactive approval prompt from AKBP. Treat that environment as read-only unless your repository has a separate human review step before any durable write is applied.

Recommended cloud-agent setup:

1. expose only read methods such as `akbp.capabilities`, `akbp.session.start`, `akbp.context`, `akbp.search`, `akbp.cite`, and `akbp.status`
2. require the `read_only` workflow profile during capability negotiation
3. keep write-capable methods such as `akbp.remember`, `akbp.ingest`, `akbp.import_apply`, `akbp.session.end`, and `akbp.index` out of the hosted tool allowlist
4. run write previews and approved applies from a local checkout or CI job that can show `review_required` and `apply_instruction` to a human reviewer

Local Copilot, terminal-assisted, or CI-backed flows can still use the normal dry-run then approved apply sequence below. The key boundary is whether a human can review the preview before the write lands.

## Startup flow

1. Discover `akbp.json` in the repository root or a parent directory.
2. Call `akbp.capabilities` before assuming method names, schemas, workflow profiles, or write behavior.
3. For hosted cloud-agent flows, require the `read_only` profile and use its method allowlist.
4. Call `akbp.context` or `akbp.session.start` with the current task before planning.
5. Cite retrieved claims when prior project knowledge affects code changes, release decisions, or recommendations.

## Write flow

Start durable writes with dry-run. Render `review_required` and `apply_instruction` before applying.

```json
{"id":"copilot-session-preview","method":"akbp.session.end","path":".","dry_run":true,"params":{"transcript":"session-summary.md","apply":true}}
```

Apply only after explicit approval or trusted local policy:

```json
{"id":"copilot-session-approved","method":"akbp.session.end","path":".","approved":true,"params":{"transcript":"session-summary.md","apply":true}}
```

For imported notes, issues, pull request summaries, or release notes, begin with ingest dry-run:

```json
{"id":"copilot-ingest-preview","method":"akbp.ingest","path":".","dry_run":true,"params":{"file":"docs/release-note.md","title":"Release note","claim":"The project validates releases with make validate.","claim_type":"workflow"}}
```

Validate JSONL imports before applying them:

```json
{"id":"copilot-import-check","method":"akbp.import_check","path":".","params":{"file":"memory-export.jsonl"}}
```

## CLI fallback

```bash
akbp --path . context "current Copilot task" --limit 8
akbp --path . crystallize session-summary.md --dry-run
```

Follow `docs/AGENT_FLOW.md`: retrieve context first, preview source imports, crystallize session knowledge with dry-run preview before apply, refresh the index after approved writes, and cite claims when prior knowledge affects work.

## Approval-gated write safety

Every adapter must use the same durable write boundary:

- call `akbp.capabilities` before assuming methods or schemas
- keep hosted cloud-agent tool integrations read-only unless a separate human approval step exists
- call `akbp.context` before planning substantial work
- start source imports with ingest dry-run
- validate JSONL exports with `akbp.import_check` and preview accepted imports with `akbp.import_apply` plus `dry_run:true`
- preview session memory with `akbp.session.end` and request-level `dry_run:true`
- surface `review_required` and `apply_instruction` before applying writes
- apply only with request-level `approved:true` after approval or trusted local policy
- Do not store secrets, tokens, cookies, auth headers, private messages, or raw logs with credentials

Follow `docs/AGENT_FLOW.md` for the complete loop.
