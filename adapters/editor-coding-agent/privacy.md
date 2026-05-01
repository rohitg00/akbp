# Editor Coding Agent Privacy Defaults

Editor agents can see broad workspace context. Keep AKBP writes narrow and reviewable.

## Never store

- API keys, tokens, cookies, private keys, auth headers, or credential-like snippets.
- Full private conversations, unsaved buffers, or editor telemetry.
- User-specific local paths unless needed for project-local evidence.

## Safe defaults

- Default durable writes to dry-run.
- Ask before applying writes or broadening scope beyond the project.
- Redact secrets before ingesting files or summaries.
- Prefer citations to source files over copying large private excerpts.
