# AKBP tool protocol Contract

## Goal

Expose AKBP through stable tool calls so any compatible agent can read, write, cite, and maintain a shared knowledge base.

## Tool naming

All tools use the `akbp.` prefix.

For tool-protocol hosts, keep AKBP's newline-delimited JSON server as the source
contract and treat the bridge layer as translation glue. Start with a read-only
tool allowlist and preserve `ok`, `result`, `error.code`, citations,
warnings, and budget fields in the host response. See `docs/TOOL_PROTOCOL_BRIDGE.md`.

## Tools

### akbp.search

Search pages, claims, entities, and evidence.

Input:

```json
{
  "query": "string",
  "limit": 10
}
```

Current backend: `sqlite_fts5`. Vector and graph retrieval are protocol roadmap items, not accepted `akbp.search` parameters in the reference tool server yet.

Output:

```json
{
  "query": "rollback release",
  "backend": "sqlite_fts5",
  "fts_query": "\"rollback\" \"release\"",
  "results": [
    {
      "type": "claim",
      "id": "claim_...",
      "path": "claims/claims.jsonl",
      "snippet": "Agents need rollback paths",
      "rank": -0.42
    }
  ]
}
```

Schema: `#/$defs/search_result`.

### akbp.context

Return compact context for an agent task.

Input:

```json
{
  "task": "string",
  "limit": 10,
  "max_chars": 4000
}
```

Output:

```json
{
  "task": "string",
  "items": [],
  "budget": {
    "max_chars": 4000,
    "summary_chars": 0,
    "original_summary_chars": 0,
    "truncated_items": 0,
    "clipped_items": 0,
    "omitted_items": 0,
    "items_before_budget": 0,
    "items_after_budget": 0
  },
  "warnings": []
}
```

### akbp.remember

Write a claim or observation.

Input:

```json
{
  "text": "string",
  "type": "observation|decision|preference|workflow|fact",
  "evidence": [],
  "entity": [],
  "dry_run": false
}
```

### akbp.session.start

Adapter-level session entrypoint. It returns a stable `session_id` and a cited context pack for the current task. Use this at runtime startup before planning or making write decisions.

```json
{
  "id": "session-start-1",
  "method": "akbp.session.start",
  "path": ".",
  "params": {"task": "continue the release", "limit": 5, "max_chars": 4000}
}
```

### akbp.session.end

Adapter-level session-end operation. It crystallizes a transcript using the same underlying behavior as `akbp.crystallize_session`, but gives adapter authors a stable operation name for session lifecycle wiring. Start with request-level `dry_run:true`; only repeat with `approved:true` and `params.apply:true` after reviewing the summary.

```json
{
  "id": "session-end-preview-1",
  "method": "akbp.session.end",
  "path": ".",
  "dry_run": true,
  "params": {"transcript": "session.md", "apply": true}
}
```

### akbp.crystallize_session

Low-level transcript crystallization operation. Prefer `akbp.session.end` for adapter lifecycle integrations. Start with request-level `dry_run:true`; only set `params.apply:true` after reviewing the summary.

Request envelope:

```json
{
  "id": "crystallize-preview",
  "method": "akbp.crystallize_session",
  "path": ".",
  "dry_run": true,
  "params": {
    "transcript": "transcript.md",
    "apply": true
  }
}
```

Output:

```json
{
  "session_id": "session_...",
  "apply": false,
  "summary": {},
  "page": "wiki/sessions/session_....md",
  "source_id": null,
  "created_claims": [],
  "skipped_claims": []
}
```

### akbp.cite

Return evidence for a claim or answer.

### akbp.supersede

Mark an old claim as replaced by a newer claim.

### akbp.conformance

Run protocol conformance checks for a requested level.

### akbp.audit

Return recent audit events.

## Safety defaults

- tool protocol write tools must support dry-run mode.
- Destructive actions must be reversible.
- Secret-like strings must be redacted before writes unless explicitly allowed by config.
- Private scopes must not be returned to agents outside their configured visibility.

## `akbp.export`

Return a portable bundle of protocol artifacts: card, claims, sources, entities, and relations. Local indexes and engine-owned state are excluded. The result includes a `manifest` with artifact paths, SHA-256 hashes when files exist, object counts, safety flags, and verification metadata so another agent can inspect the bundle before accepting it.

## `akbp.source.verify`

Re-check recorded file sources against their stored SHA-256 hashes. The result separates verified, changed, missing, and unchecked sources so agents can catch evidence drift before relying on old claims. When drift or missing evidence is found, `attention` lists the changed or missing source ids, unique affected claim ids, and a `recommended_action` adapters can surface before trusting recalled memory.

## `akbp.export_check`

Validate a portable export bundle before another agent trusts it. The check verifies JSON shape, manifest presence, object counts, artifact hash format, safety flags, and secret-like values. Use `fail_on_issues:true` in automation when any issue should stop the workflow.

## `akbp.audit`

Return recent audit events, optionally filtered by event type.

## JSONL reference server

`tool-server/akbp_tool_server.py` is a dependency-free JSONL server for local agent integrations. It reads one JSON request per line and writes one JSON response per line.

Supported JSONL methods:

- `akbp.capabilities`
- `akbp.status`
- `akbp.doctor`
- `akbp.query`
- `akbp.context`
- `akbp.index`
- `akbp.search`
- `akbp.remember`
- `akbp.conformance`
- `akbp.export`
- `akbp.export_check`
- `akbp.audit`
- `akbp.cite`
- `akbp.source.add`
- `akbp.source.verify`
- `akbp.ingest`
- `akbp.import_check`
- `akbp.import_apply`
- `akbp.supersede`
- `akbp.contradict`
- `akbp.crystallize_session`
- `akbp.session.start`
- `akbp.session.end`

The CLI also has local-only commands such as `akbp lint`; those are not JSONL server methods unless listed above.

Request and response envelopes are specified in:

- `schemas/tool-request.schema.json`
- `schemas/tool-response.schema.json`
- `schemas/tool-methods.schema.json`

`akbp.capabilities` returns these schema URLs under `result.schemas`, returns runtime policy under `result.runtime`, returns each method's `params_schema` reference when a method-specific contract exists, returns adapter-oriented method groups under `result.profiles`, and advertises enforcement features for method parameter schemas, bounded context retrieval, session lifecycle entrypoints, capability negotiation, unknown request-field rejection, unknown-parameter rejection, required-parameter validation, structured approval-required errors, request-size enforcement, request-id string validation, request-id numeric bounds, path validation, string parameter length validation, path-like parameter control-character validation, evidence/entity array validation, and dry-run argv redaction. Runtime policy includes JSONL stdio transport, default path behavior, request-size, request-id string length, and request-id numeric bounds, caller-supplied local path policy, string parameter length policy, context budget policy for `akbp.context` and `akbp.session.start`, path-like parameter control-character policy, evidence/entity array count and item-length policy, supported hash algorithms, dry-run support, review-gated writes, the approval field name, and `method_schema_runtime_errors` so adapters can surface schema/runtime drift instead of guessing.

`result.profiles` is a discovery shortcut for adapters that need workflow intent instead of a flat method list:

- `read_only`: discovery, status, retrieval, validation, export checks, audit, citation, source verification, import checks, and session-start context methods that do not mutate the knowledge base.
- `startup_context`: capability discovery, status, session start, context, and search methods for startup retrieval.
- `reviewed_write`: write methods that should be previewed with `dry_run:true` before approved application.
- `lifecycle`: supersession, contradiction, crystallization, audit, and citation methods for maintaining memory over time.
- `portability`: export, export check, import check, and import apply methods for bundle exchange.
- `maintenance`: doctor, index, source verification, and conformance methods for local upkeep.

Adapters may pass optional capability negotiation params to `akbp.capabilities`: `client` is a short adapter identifier, `requires` is a bounded list of required feature names such as `method_param_schemas` or `features.capability_negotiation`, and `requires_profiles` is a bounded list of workflow profiles such as `read_only` or `startup_context`. The response always includes `result.negotiation` with requested, supported, unsupported, and `satisfied` fields for both features and profiles. Treat `satisfied:false` as a graceful-degrade signal, not a transport failure.

For low-context agent harnesses, negotiate `features.bounded_context` and use `akbp.session.start` or `akbp.context` with `max_chars`. This lets the adapter request compact cited startup context instead of pasting full `AKBP.md`, wiki, or JSONL artifacts into every run. The returned `budget` object separates clipped summaries from omitted items and reports item counts before and after budgeting so adapters can fail closed, lower `limit`, or ask for a larger budget without parsing warning prose.

`tool-methods.schema.json` defines method-specific parameter contracts for every supported JSONL method. Shared list contracts are bounded before CLI dispatch: `evidence` accepts at most 64 string items of 512 characters each, and `entity` accepts at most 128 string items of 256 characters each. Both reject NUL, newline, and carriage-return characters.

Supported method contracts include:

- `akbp.capabilities`
- `akbp.status`
- `akbp.doctor`
- `akbp.query`
- `akbp.context`
- `akbp.index`
- `akbp.search`
- `akbp.remember`
- `akbp.conformance`
- `akbp.export`
- `akbp.export_check`
- `akbp.audit`
- `akbp.cite`
- `akbp.source.add`
- `akbp.source.verify`
- `akbp.ingest`
- `akbp.import_check`
- `akbp.import_apply`
- `akbp.supersede`
- `akbp.contradict`
- `akbp.crystallize_session`
- `akbp.session.start`
- `akbp.session.end`

Every response uses the same envelope:

```json
{
  "id": "request-id",
  "ok": true,
  "result": {},
  "error": null
}
```

Errors are structured:

```json
{
  "id": "request-id",
  "ok": false,
  "result": null,
  "error": {
    "code": "unknown_method",
    "message": "unknown method: akbp.missing",
    "details": {
      "available_methods": []
    }
  }
}
```

The response schema also names common result and error detail shapes used by adapters:

- `#/$defs/capabilities_result`: the closed capability discovery result with protocol, feature flags, schema URLs, methods, adapter workflow profiles, and examples.
- `#/$defs/context_result`: a closed `akbp.context` result with query, generated timestamp, context items, warnings, and optional budget metadata for bounded context requests.
- `#/$defs/search_result`: a closed `akbp.search` result with query, backend, optional FTS query, result rows, and warnings such as skipped inactive matching claims.
- `#/$defs/status_result`: a closed `akbp.status` result with path, legacy object counts, initialization flags, latest claims, source verification health, audit count, index presence, and highest passing conformance level.
- `#/$defs/doctor_result`: a closed `akbp.doctor` result with pass/fail checks, profile-specific adapter readiness, recommended adapter profile, and actionable next steps.
- `#/$defs/index_result`: a closed approved `akbp.index` result with database path, row counts, indexed/skipped/removed counts, incremental mode, and doc keys for indexed, skipped, and removed items.
- `#/$defs/cite_result`: a closed `akbp.cite` result with claim id, text, evidence list, and status.
- `#/$defs/audit_result`: a closed `akbp.audit` result with audit events and count.
- `#/$defs/export_result`: a closed `akbp.export` result with version, timestamp, card, claims, sources, entities, and relations.
- `#/$defs/context_item`: the closed nested item shape returned by `akbp.context`.
- `#/$defs/search_result_row`: the closed nested result-row shape returned by `akbp.search`.
- `#/$defs/audit_event`: the closed nested event shape returned by `akbp.audit`.
- `#/$defs/exported_claim`: the closed nested claim shape returned by `akbp.export`.
- `#/$defs/claim_result`: the closed claim shape returned by approved `akbp.remember` and `akbp.supersede`.
- `#/$defs/source_result`: the closed source record returned by approved `akbp.source.add` and nested in `akbp.export`.
- `#/$defs/entity_result`: the closed entity record nested in `akbp.export`.
- `#/$defs/relation_result`: the closed relation record returned by approved `akbp.contradict` and nested in `akbp.export`.
- `#/$defs/dry_run_review_result`: a closed generic dry-run write result with `dry_run:true`, `would_write:true`, `method`, `path`, redacted `argv`, `redacted`, `review_required:true`, and `apply_instruction`.
- `#/$defs/ingest_dry_run_result`: a closed `akbp.ingest` dry-run preview with redaction status, extracted signals, planned claim ids, `would_write` paths, and review metadata.
- `#/$defs/ingest_result`: a closed approved `akbp.ingest` result with source id, imported page path, extracted signals, created claim ids, and redaction status.
- `#/$defs/import_check_result`: a closed `akbp.import_check` result with checked, accepted, rejected, and error counts, strict-fail mode status, accepted object ids, rejected object ids, unknown source-evidence rejection, duplicate import-id rejection, scalar collection-field rejection, parse errors without raw secret echo, and `review` metadata for adapter approval gates. The review metadata includes both uncited claims and claims whose evidence does not link to a registered source id.
- `#/$defs/import_apply_result`: a closed `akbp.import_apply` result with dry-run/apply status, accepted counts, rejected counts, would-write ids, duplicate import-id rejection, scalar collection-field rejection, skipped-existing ids, and optional `review` metadata. Review `review.ready_for_reviewed_apply`, `review.claims_without_evidence`, `review.claims_without_source_evidence`, `accepted_count`, `rejected_count`, `error_count`, `would_write.sources`, and `would_write.claims` before repeating the request with `approved:true`.
- `#/$defs/crystallize_session_result`: a closed approved session crystallization result with `session_id`, extracted closed `summary`, output page, source id, created claims, and skipped claims.
- `#/$defs/session_start_result`: a closed adapter session-start result with `session_id`, task, and cited context pack.
- `#/$defs/session_end_preview_result`: a closed session-end dry-run result with extracted summary, planned page, review metadata, and no durable writes.
- `#/$defs/approval_required_details`: a closed `approval_required` error details object with `dry_run:false`, `review_required:true`, and `apply_instruction`.
- `#/$defs/invalid_request_details`: closed request-envelope validation details with `errors` and `schema`.
- `#/$defs/invalid_json_details`: closed invalid JSON line details with parse `errors` and the request-envelope `schema`, without echoing the raw input line.
- `#/$defs/cli_error_details`: closed CLI execution failure details with `method`, `exit_code`, redacted captured `stdout`, and a `redacted` flag.
- `#/$defs/internal_error_details`: closed defensive server-boundary failure details with sanitized `errors`.
- `#/$defs/invalid_params_details`: closed parameter validation details with `params_schema` plus missing, unknown, allowed, or type-error metadata when relevant.
- `#/$defs/unknown_method_details`: closed unknown-method details with the advertised `available_methods` list.

The response schema intentionally leaves only four nested extension pockets open: capability example `params`, export `card`, audit event `data`, and source `metadata`. Tests reject any new open `additionalProperties:true` location unless it is deliberately documented here.

Adapters should treat the write-review shapes as control-flow contracts. They are not advisory prose. A dry-run result must be rendered for review, and an `approval_required` error must stop the apply path until the caller repeats the request with `approved:true` after approval or trusted local policy.

## Write-mode safety

Write-capable methods must be treated as reviewable operations by default.

Agents should:

1. call `akbp.capabilities` first and check the advertised method list and `params_schema` references
2. use request-level `dry_run: true` before the first write in a session
3. show the planned write to the user or calling runtime when approval is required
4. repeat the same request with `approved: true` and without `dry_run` only after approval or trusted local policy
5. keep writes local to the caller-supplied knowledge-base path unless the user explicitly chooses another path
6. cite evidence for durable claims and avoid storing transient logs
7. redact secret-like strings before sending write requests

Write methods support request-level dry run:

```json
{"id":"1","method":"akbp.remember","path":".","dry_run":true,"params":{"text":"Agents need rollback paths","type":"workflow","evidence":["release-notes.md"]}}
```

Dry-run write responses return planned command arguments and do not mutate the knowledge base. Non-ingest write dry-runs also include `review_required:true` and an `apply_instruction` telling clients to repeat the same request without `dry_run` only after user approval or trusted local policy. Clients should render them as a reviewable change, not as committed memory. Non-dry-run write requests must include request-level `approved:true`; otherwise the server returns `approval_required`.

Approved apply example:

```json
{"id":"1-apply","method":"akbp.remember","path":".","approved":true,"params":{"text":"Agents need rollback paths","type":"workflow","evidence":["release-notes.md"]}}
```

Importing a local file through the JSONL server should also start with dry-run when the caller is unsure about scope or content sensitivity:

```json
{"id":"2","method":"akbp.ingest","path":".","dry_run":true,"params":{"file":"notes.md","claim":"The project ships small verified batches","claim_type":"decision"}}
```

For `akbp.ingest`, dry-run executes the CLI preview and returns redacted import metadata instead of only argv: `source_id`, page path, extracted signals, claim ids, redaction status, and `would_write` paths. It also includes `review_required:true` and an `apply_instruction` focused on reviewing redaction and planned writes. It does not create source, claim, page, log, audit, or index files. In apply mode, ingested source content, optional claim text, and source titles are redacted before durable writes.

Agents can also manage the local search index and query it. The index covers claims, markdown pages, source records, entity records, and relation records so structured JSONL knowledge can be retrieved without relying on page mirrors. Search supports conservative SQLite FTS5 syntax: plain terms default to OR, quoted phrases are preserved, `AND`/`OR`/`NOT` are accepted, punctuation is sanitized, trailing malformed operators are removed, and trailing `*` enables safe prefix matches for simple word tokens. Queries with no safe searchable terms, including a leading standalone `NOT` or operator-only text, return `sqlite_fts5` with an empty `fts_query` and empty result set instead of falling back to broad text scanning. Search and context retrieval skip inactive claims such as superseded, archived, redacted, or superseded-by claims and return warnings when an inactive claim matched the query. They also warn when returned claims cite file sources whose recorded hashes are now changed or missing; adapters should surface those warnings before relying on the cited context.

```json
{"id":"3","method":"akbp.index","path":".","approved":true,"params":{"incremental":true}}
{"id":"4","method":"akbp.search","path":".","params":{"query":"rollback release","limit":5}}
{"id":"5","method":"akbp.search","path":".","params":{"query":"migrat* AND rollback","limit":5}}
```
