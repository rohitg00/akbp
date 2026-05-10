# AKBP Benchmark Fixtures

These fixtures are small, deterministic scenarios for evaluating durable agent knowledge behavior.

They are not leaderboard scores. They define reusable inputs and expected outcomes for future benchmark runners.

## Fixture format

Each fixture directory contains:

```text
scenario.json
```

The scenario file includes:

- `id`: stable fixture id
- `task`: behavior being evaluated
- `setup`: sources, claims, relations, import objects, proposed claims, or JSONL `tool_server_requests`
- `query`: retrieval or maintenance question
- `expected`: pass criteria

`tool_server_requests` can declare:

- `expected_result_fields`: fields that must exist in successful `result` payloads
- `expected_result_values`: exact values that must match in successful `result` payloads
- `expected_result_schema`: optional `#/$defs/...` response schema reference used to reject missing required fields or unexpected top-level fields
- `expected_error_code`: structured error code expected for rejected requests
- `expected_error_schema`: optional `#/$defs/...` error-details schema reference used to reject missing required fields or unexpected fields in `error.details`
- `expected_error_fields`: fields that must exist in structured `error.details`
- `expected_error_values`: exact values that must match in structured `error.details`
- `expected_error_contains`: nested-path contains checks for structured `error.details`, including arrays such as `allowed[]` and `type_errors[]`

Any field checked in `expected_result_values` or `expected_error_values` must also be listed in the corresponding field list, so fixtures document the complete contract they validate.

## Current fixtures

- `adapter-write-safety`: require runtime adapters to share the same dry-run, review metadata, approved write, and privacy boundary.
- `adapter-session-operation`: verify adapter session start/end lifecycle operations and compatibility shapes.
- `preference-recall`: recall a durable user preference with evidence.
- `supersession`: prefer a newer claim while preserving the old claim.
- `contradiction`: detect conflicting claims and require resolution.
- `correction-resolution`: prefer a newer correction while preserving old conflicting knowledge until explicit resolution.
- `secret-safety`: reject or redact secret-like text before durable writes.
- `import-safety`: validate JSONL import objects, normal plus strict `akbp.import_check` responses, and rejected `akbp.import_apply` preview result shapes before durable writes.
- `export-bundle-compatibility`: validate portable bundle manifest counts, artifact hash shape, safety flags, and strict failure results.
- `invalid-param-rejection`: validate schema-backed `invalid_params` details for unknown, zero-param method unknown, missing required method params, wrong-typed, wrong item-typed, out-of-range, boolean flag, oversized string, import/export file-param, source verification id, cite claim id, claim relation id, audit limit, read-method limit, conformance level, lifecycle method params, and unsupported enum method parameters before CLI execution.
- `import-apply-flow`: validate JSONL `akbp.import_apply` dry-run and approved apply responses before durable writes.
- `import-compatibility-edges`: validate mixed JSONL compatibility for accepted source/claim records, unknown evidence ids, unsupported kinds, invalid claim shapes, and scalar collection-field rejection.
- `import-apply-malformed`: validate import apply returns schema-backed failure results for malformed JSONL before durable writes.
- `import-apply-skipped-existing`: validate import apply reports existing source and claim records through `skipped_existing` instead of rewriting them.
- `graph-jsonl-records`: populate real JSONL entities and relations and validate schema-backed export.
- `session-crystallization`: retrieve workflow claims from a structured coding-agent session with citations.
- `multi-agent-handoff`: retrieve cited context from prior agent sessions before continuing adapter work.
- `review-gated-writes`: require agents to honor dry-run review metadata before applying durable writes.
- `read-method-schema`: verify read-only JSONL methods, including capability discovery and audit, return schema-backed response shapes without write approval, including advertised enforcement flags and method schema references.
- `retrieval-citation-bundle`: verify context retrieval and citation lookup return the same evidence-backed claim through JSONL tool calls.
- `retrieval-ambiguity-ranking`: verify ambiguous adapter lifecycle queries retrieve the direct lifecycle and validation claims with citations.
- `retrieval-noisy-evidence`: verify direct, cited lifecycle decisions are returned despite noisy adjacent memory and launch-copy claims.
- `search-index-observability`: verify safe prefix search and incremental index document-key observability through JSONL tool calls.
- `search-query-compatibility`: verify phrase, version, hyphenated, slash-separated, prefix, mixed operator-plus-prefix, empty, and malformed-operator FTS query compatibility.
- `write-preview-crystallize-schema`: verify ingest dry-run previews, approved ingest, and approved session crystallization return schema-backed results.
- `approved-write-apply`: verify approved JSONL write calls return concrete records that adapters can inspect after approval.
- `unapproved-write-rejection`: verify non-dry-run JSONL writes, including import apply, without `approved:true` return structured `approval_required` errors.
- `unknown-method-rejection` checks that unsupported JSONL tool methods return structured `unknown_method` errors with advertised alternatives.
- `capability-negotiation` checks that runtimes can discover method schemas, structured errors, and write-review policy before invoking tools.
