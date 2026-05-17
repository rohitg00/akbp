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
- `expected_error_stdout_contains`: nested-path contains checks after parsing JSON `error.details.stdout`, for fail-closed commands that preserve diagnostics in CLI stdout

Any field checked in `expected_result_values` or `expected_error_values` must also be listed in the corresponding field list, so fixtures document the complete contract they validate.

Scenarios may include `profiles` to opt into focused benchmark slices. For
example, `profiles: ["adapter-quality"]` lets adapter authors run only the
quality-gate fixtures with `make adapter-quality` while they are wiring a new
runtime.

## Current fixtures

- `adapter-write-safety`: require runtime adapters to share the same dry-run, review metadata, approved write, and privacy boundary.
- `adapter-structured-output-harness`: verify adapter quality gates can machine-check capability negotiation, doctor/security posture, bounded startup context, dry-run preview metadata, and approval-gated write rejection before trusting memory.
- `adapter-session-operation`: verify adapter session start/end lifecycle operations and compatibility shapes.
- `bounded-context-citation-lifecycle`: verify bounded startup context keeps citations and lifecycle freshness while skipping superseded long-context memory.
- `branch-aware-handoff`: verify branch-local handoff memory preserves branch scope, citations, and review gates before reuse on another checkout.
- `context-pressure-budget`: verify tight startup context reports budget truncation while preserving the highest-value cited memory item.
- `contested-memory-planning-gate`: verify adapters fail closed before planning from retrieved claims whose lifecycle status is contested.
- `compaction-handoff-recall`: verify compaction handoffs retrieve the current cited decision instead of stale relative-date memory.
- `git-native-agent-handoff`: verify git-native agent adapters retrieve cited handoff context and review-gated write policy before continuing repository work.
- `inherited-repo-intake`: verify agents entering unfamiliar repositories discover AKBP, run adapter readiness checks, retrieve cited startup context, and keep durable writes disabled until trust gates pass.
- `knowledge-gap-to-task`: verify recent adoption research can become a cited, reviewable product task before new adapter or write-transport work starts.
- `preference-recall`: recall a durable user preference with evidence.
- `supersession`: prefer a newer claim while preserving the old claim.
- `contradiction`: detect conflicting claims and require resolution.
- `correction-resolution`: prefer a newer correction while preserving old conflicting knowledge until explicit resolution.
- `secret-safety`: reject or redact secret-like text before durable writes.
- `import-safety`: validate JSONL import objects, normal plus strict `akbp.import_check` responses, and rejected `akbp.import_apply` preview result shapes before durable writes.
- `long-document-ingest`: verify longer source documents produce section-level ingest signals through dry-run review, approved apply, indexing, and retrieval.
- `memory-server-bridge`: verify tool-protocol memory server or runtime-cache rows become durable AKBP knowledge only after source-backed import-check, dry-run review, explicit approval, indexing, and cited context recall.
- `native-memory-interop`: verify product-native memory and external memory tools stay ephemeral until AKBP retrieves cited startup context, promotes source-backed facts through dry-run review and approved apply, and uses lifecycle relations for conflicts.
- `multi-agent-consistency`: verify shared agent knowledge preserves supersession history while retrieving the current cited decision for later agents.
- `export-bundle-compatibility`: validate portable bundle manifest counts, artifact hash shape, safety flags, and strict failure results.
- `existing-memory-migration`: verify existing agent-memory exports are imported only when source-backed, dry-run reviewed, and explicitly approved.
- `invalid-param-rejection`: validate schema-backed `invalid_params` details for unknown, zero-param method unknown, missing and partial missing required method params, file/source verification missing params, wrong-typed, wrong item-typed, out-of-range, boolean flag, oversized string, import/export file-param, source verification id, cite claim id, claim relation id, audit limit, read-method limit, conformance level, lifecycle method params, and unsupported enum method parameters before CLI execution.
- `import-apply-flow`: validate JSONL `akbp.import_apply` dry-run and approved apply responses before durable writes.
- `import-compatibility-edges`: validate mixed JSONL compatibility for accepted source/claim records, unknown evidence ids, unsupported kinds, invalid claim shapes, and scalar collection-field rejection.
- `import-apply-malformed`: validate import apply returns schema-backed failure results for malformed JSONL before durable writes.
- `import-apply-skipped-existing`: validate import apply reports existing source and claim records through `skipped_existing` instead of rewriting them.
- `graph-jsonl-records`: populate real JSONL entities and relations and validate schema-backed export.
- `session-crystallization`: retrieve workflow claims from a structured coding-agent session with citations.
- `multi-agent-handoff`: retrieve cited context from prior agent sessions before continuing adapter work.
- `review-gated-writes`: require agents to honor dry-run review metadata before applying durable writes.
- `read-method-schema`: verify read-only JSONL methods, including capability discovery and audit, return schema-backed response shapes without write approval, including advertised enforcement flags and method schema references.
- `read-only-adapter-profile`: verify new adapters can use `result.profiles.read_only` as a safe allowlist before implementing reviewed write UX.
- `retrieval-citation-bundle`: verify context retrieval and citation lookup return the same evidence-backed claim through JSONL tool calls.
- `retrieval-ambiguity-ranking`: verify ambiguous adapter lifecycle queries retrieve the direct lifecycle and validation claims with citations.
- `retrieval-noisy-evidence`: verify direct, cited lifecycle decisions are returned despite noisy adjacent memory and launch-copy claims.
- `retrieval-structured-jsonl-objects`: verify richer source, claim, entity, and relation JSONL objects retrieve precise AgentMemory operational memory and export graph context.
- `search-index-observability`: verify safe prefix search and incremental index document-key observability through JSONL tool calls.
- `search-query-compatibility`: verify phrase, version, hyphenated, slash-separated, prefix, mixed operator-plus-prefix, empty, and malformed-operator FTS query compatibility.
- `source-truth-drift`: verify changed repository source files are surfaced as review blockers before adapters trust recalled project memory.
- `startup-context-relevance`: verify persistent memory adapters retrieve task-relevant cited startup context instead of dumping broad memory-server rows into every new session.
- `write-preview-crystallize-schema`: verify ingest dry-run previews, approved ingest, and approved session crystallization return schema-backed results.
- `workflow-scoped-context`: verify adapters with a selected workflow or node retrieve cited startup context scoped to that active workflow instead of broad repository memory.
- `approved-write-apply`: verify approved JSONL write calls return concrete records that adapters can inspect after approval.
- `unapproved-write-rejection`: verify non-dry-run JSONL writes, including import apply, without `approved:true` return structured `approval_required` errors.
- `unknown-method-rejection` checks that unsupported JSONL tool methods return structured `unknown_method` errors with advertised alternatives.
- `capability-negotiation` checks that runtimes can discover method schemas, structured errors, and write-review policy before invoking tools.
- `tool-output-presentation`: verify `akbp.search` and `akbp.context` preserve the same cited evidence under inline and file `output_mode`, so a harness can grep or stream a JSONL artifact instead of inlining results. Motivated by recent agent-harness research showing that tool-output presentation choice influences agentic retrieval scores independent of the underlying data; see `docs/HARNESS_AND_PRESENTATION.md`.
