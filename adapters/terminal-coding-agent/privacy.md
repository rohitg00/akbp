# Terminal Coding Agent Privacy Defaults

Terminal agents often see sensitive local output. Store less by default.

## Never store

- API keys, tokens, cookies, private keys, auth headers, or `.env` contents.
- Full shell histories, raw logs, process lists, or environment dumps.
- Private file paths unless they are necessary evidence for a project-local claim.

## Safe defaults

- Prefer project-local scope.
- Use dry-run before write-capable tool calls.
- Redact suspicious credential-like strings before ingesting files or summaries.
- Cite source files rather than copying large command outputs into claims.
