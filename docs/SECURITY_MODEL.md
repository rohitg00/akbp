# AKBP security model

AKBP is a local-first durable knowledge protocol. The reference implementation is designed for agent memory, so security work focuses on preventing accidental durable storage of secrets, making writes reviewable, and keeping protocol artifacts portable without exposing private runtime state.

## Trust boundaries

| Boundary | What crosses it | Required control |
| --- | --- | --- |
| Agent runtime to JSONL tool server | Method requests, request ids, paths, params, write intent | Closed request envelopes, method schemas, request-size limits, bounded request-id strings, path validation, file/path string length caps, bounded evidence/entity arrays, structured errors |
| Tool server to local knowledge base | Source records, pages, claims, graph records, audit logs | Review-gated writes, dry-run previews, redaction before durable writes |
| Local knowledge base to portable bundle | Export manifest and protocol artifacts | Export checks, manifest validation, secret-like value rejection |
| Imported bundle to local knowledge base | JSONL source and claim records | Import checks, evidence validation, dry-run apply previews |
| Search index to agent context | Retrieved snippets and citations | Local index only, explicit query, citation-backed context |

## Write safety contract

Write-capable flows must be reviewable before durable writes:

1. Run the operation in dry-run mode.
2. Review the returned `would_write`, redaction status, source ids, claim ids, and apply instruction.
3. Apply only with explicit approval.
4. Keep audit records for applied operations.

The JSONL tool server enforces this for write methods with request-level `dry_run:true` and `approved:true` gates. A rejected write should return a structured `approval_required` error rather than partially mutating the knowledge base.

## Secret-handling expectations

The reference implementation redacts common secret-like values from ingested source content, optional ingest claim text, ingest source titles, generic dry-run argv previews, and import/export validation paths. Implementations should treat redaction as defense in depth, not as permission to ingest private data blindly.

Do not intentionally store:

- API keys, access tokens, refresh tokens, cookies, passwords, private keys, or auth headers
- connection strings with embedded credentials
- private messages or personal data without permission and clear task relevance
- raw logs that include secrets when a smaller evidence-backed claim is sufficient

## Local state and portability

Portable AKBP artifacts should contain useful durable knowledge and evidence references. Local engine state, caches, index files, process state, temporary files, and adapter-private metadata should stay outside portable bundles unless explicitly documented and reviewed.

## Adapter requirements

Adapters should:

- call `akbp.capabilities` before assuming method support
- enforce advertised request and parameter policies, including closed request envelopes, string length caps for import/export file params, path-like control-character rejection, and evidence/entity array bounds
- start write-capable operations with dry-run previews
- surface review metadata to the user or supervising runtime
- never auto-approve writes by default
- avoid passing full private transcripts when a concise task summary is enough
- preserve citations and source ids when presenting recalled context

## Reporting

Report security issues privately to the repository owner. Do not open public issues with live secrets, tokens, private keys, cookies, production credentials, private user data, or exploit-ready sensitive material.
