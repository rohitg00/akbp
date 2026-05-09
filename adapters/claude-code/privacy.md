# Claude Code Adapter Privacy

Use AKBP for concise, cited, durable project knowledge. Do not use it as a raw transcript dump.

## Do store

- Project decisions with evidence.
- Stable repo-specific workflow preferences.
- Blockers, follow-up actions, and open questions.
- Source references that can be cited later.

## Do not store

- Secrets, tokens, cookies, auth headers, API keys, or connection strings.
- Private DMs or personal contact data.
- Raw command logs that may contain credentials.
- Large transcripts when a concise summary is enough.

## Write safety

- Default to project scope.
- Use ingest dry-run for imported files.
- Use `akbp.session.end` dry-run for session memory.
- Treat `review_required` and `apply_instruction` as mandatory obligations.
- Apply writes only with `approved:true` after approval or trusted local policy.

Follow `docs/AGENT_FLOW.md` and `docs/TOOL_CONTRACT.md` for the full safety model.
