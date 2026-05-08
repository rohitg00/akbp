# Adapter Review Checklist

Use this checklist before publishing or updating an AKBP adapter for any coding agent runtime.

## Capability discovery

- Start every session by calling `akbp.capabilities`.
- Read advertised `methods` instead of assuming a local method list.
- Use `params_schema` links when validating runtime-generated calls.
- Treat missing methods as unsupported and stop instead of guessing a replacement.

## Retrieval before work

- Call `akbp.context` before substantial planning or code changes.
- Use `akbp.search` for targeted lookup when a user asks about prior decisions, known constraints, or project facts.
- Cite claims with `akbp.cite` when retrieved knowledge materially affects an answer or implementation.

## Write safety

- Start every write-capable operation with request-level `dry_run:true`.
- Surface `review_required`, `apply_instruction`, and would-write paths to the runtime review layer.
- Apply writes only with request-level `approved:true` after user approval or trusted local policy.
- Never turn a failed dry run into a non-dry-run write.

## Source and import safety

- Use ingest dry-run before adding source-backed knowledge.
- Run `akbp.import_check` before `akbp.import_apply` for JSONL exchanges.
- Reject imports with secret-like values, malformed JSONL, unknown evidence ids, or failed review counts.
- Keep source scope project-local unless the adapter has an explicit broader policy.

## Privacy and public repo hygiene

- Do not store secrets, tokens, cookies, auth headers, private DMs, or raw logs with credentials.
- Do not add provider-specific private paths to public examples.
- Keep adapter names generic unless the adapter is intentionally runtime-specific.
- Run `make validate` before publishing adapter changes.
