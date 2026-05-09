# OpenClaw Adapter Instructions

Use AKBP as the durable knowledge layer for project facts, decisions, preferences, blockers, and handoffs.

## At session start

- Locate `akbp.json` in the workspace or parent directories.
- Call `akbp.capabilities` before assuming method names, schemas, or write behavior.
- Call `akbp.context` with the current task before making a plan.
- Treat returned citations as evidence, not as hidden memory.

## During work

- Prefer cited claims over uncited recollection when prior state matters.
- Do not store secrets, tokens, cookies, private DMs, auth headers, or raw browser/session data.
- Keep scope project-local by default unless the user explicitly asks for a broader durable note.
- Start write-capable calls with request-level `dry_run:true`.
- Validate external JSONL exports with `akbp.import_check` before applying them.
- Preview accepted JSONL imports with `akbp.import_apply` and `dry_run:true`; apply only after review with request-level `approved:true`.
- If a dry-run response includes `review_required`, render the planned write and `apply_instruction` before applying.
- Apply only with request-level `approved:true` after user approval or trusted local policy.

## At session end

- Summarize durable decisions, actions, blockers, preferences, and open questions into a transcript file.
- Preview crystallization with `akbp.session.end` and `dry_run:true`.
- Apply only after approval.
- Refresh search with approved `akbp.index` when durable writes landed.

Follow `docs/AGENT_FLOW.md` for the canonical loop.
