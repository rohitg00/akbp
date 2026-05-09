# OpenClaw Adapter Privacy

OpenClaw integrations should keep AKBP durable knowledge useful, cited, and safe.

## Do store

- Project decisions with evidence.
- Stable user preferences that affect future work.
- Blockers, follow-up actions, and open questions.
- Public or project-local source references that can be cited.

## Do not store

- Secrets, tokens, cookies, API keys, auth headers, or connection strings.
- Private DMs, contact data, or browser/session dumps.
- Raw command logs that may include credentials.
- Large transcript blobs when a concise cited summary is enough.

## Write safety

- Default to project scope.
- Use ingest dry-run for imported files or source notes.
- Use `akbp.session.end` dry-run for transcript-backed memory.
- Treat `review_required` and `apply_instruction` as mandatory UI/runtime obligations.
- Apply writes only with `approved:true` after approval or trusted local policy.

Follow `docs/AGENT_FLOW.md` and `docs/TOOL_CONTRACT.md` for the full safety model.
