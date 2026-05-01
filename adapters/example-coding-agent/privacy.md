# Example Coding Agent Privacy Defaults

Use conservative defaults.

## Never store

- API keys, tokens, cookies, private keys, session secrets, or auth headers.
- Raw private conversations unless the user explicitly asks and the scope allows it.
- Full command logs, environment dumps, or private local paths unless they are necessary evidence.

## Safe defaults

- Prefer project-local scope.
- Use dry-run before write-capable calls.
- Redact credential-like strings before ingesting files or summaries.
- Cite source files instead of copying large private excerpts.
