# AKBP Adapter Privacy Defaults

Adapters must use conservative defaults.

## Never store

- API keys, tokens, cookies, private keys, session secrets, or auth headers.
- Raw private messages unless the user explicitly asks and the scope allows it.
- Credentials hidden inside command output, stack traces, URLs, or environment dumps.

## Prefer storing

- Durable technical decisions.
- User preferences that affect future work.
- Project workflows and known blockers.
- Evidence-backed facts with citations.

## Write safety

- Default to dry-run for uncertain writes.
- Ask before increasing scope from project-local to team or public.
- Supersede stale claims instead of deleting audit history.
