# Codex Adapter Instructions

Use AKBP as the durable knowledge layer for project decisions, preferences, blockers, and handoffs.

## Before planning

- Locate `akbp.json` in the current repository or parent directories.
- Call `akbp.capabilities` to inspect supported methods, schemas, and write review rules.
- Call `akbp.context` with the current task.
- Treat returned citations as evidence, not hidden memory.

## During implementation

- Prefer cited AKBP claims over unstated recollection when prior work matters.
- Keep durable memory project-scoped by default.
- Do not store secrets, tokens, cookies, private DMs, auth headers, or raw logs with credentials.
- Start write-capable JSONL calls with request-level `dry_run:true`.
- Validate external JSONL exports with `akbp.import_check` before applying them.
- Preview accepted JSONL imports with `akbp.import_apply` and `dry_run:true`; apply only after review with request-level `approved:true`.
- Surface `review_required` and `apply_instruction` before applying.
- Apply writes only with request-level `approved:true` after user approval or trusted local policy.

## End of session

- Summarize durable decisions, actions, blockers, preferences, and open questions in a local transcript summary.
- Preview with `akbp.session.end` and `dry_run:true`.
- Apply only after approval.
- Refresh search with approved `akbp.index` if durable writes landed.

Follow `docs/AGENT_FLOW.md` for the canonical loop.
