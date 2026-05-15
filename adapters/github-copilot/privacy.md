# GitHub Copilot Adapter Privacy

AKBP should store durable project knowledge, not private conversation exhaust.

## Allowed by default

- reviewed project decisions
- source-backed release or build workflows
- issue, pull request, or documentation summaries that are already appropriate for the repository
- durable preferences that affect future project work
- public-safe handoffs and open questions

## Excluded by default

- secrets, tokens, cookies, auth headers, and credentials
- private messages or private chat excerpts
- raw production logs with identifiers or credentials
- personal data that is not required for project work
- unreviewed assistant speculation

## Runtime boundary

Product-local memory can help a single assistant session, but AKBP is the reviewed file-backed project layer. Durable writes must be explicit, cited, and review-gated with `dry_run:true` before `approved:true`.

Follow `docs/AGENT_FLOW.md` and `docs/SECURITY_MODEL.md` for the complete privacy and write-safety model.
