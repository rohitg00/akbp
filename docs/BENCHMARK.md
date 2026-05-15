# AKBP Benchmark

## Purpose

AKBP needs an evaluation harness so the protocol does not become vibes.

The benchmark stance is deliberately skeptical: AKBP should prove repeated-session recall, citation quality, contradiction handling, and retrieval behavior against fixtures before claiming broad memory quality. See `docs/CRITIQUE_RESPONSE.md` for the critique-to-work mapping.

Recent agent-output discussions keep circling the same practical pattern:
structured prompts help, but teams still need a harness that proves the
runtime used the structure correctly. For AKBP, that harness is not a separate
scoring product. It is the combination of:

- capability negotiation that advertises the available method schemas
- `akbp.doctor` checks that stop adapters before unsafe writes
- `akbp.session.start` checks that cited startup context exists before planning
- dry-run write previews with schema-backed result shapes
- benchmark fixtures that assert exact response fields, nested values, and error
  codes instead of relying on prose

Use this as the agent output quality harness when you are testing a new adapter:
the agent is allowed to continue only when the JSONL responses satisfy the
fixture contract. If the response shape drifts, the adapter should fail the
harness before a user trusts the memory.

## Benchmark tasks

### 1. Preference recall

Session 1: user states a durable preference.
Session 2: agent must apply it without being reminded.

Pass criteria: correct recall with citation.

### 2. Decision recall

Session 1: project decision is made.
Session 2: agent must retrieve the decision and avoid contradicting it.

Pass criteria: cites decision claim and source.

### 3. Contradiction detection

Ingest two conflicting claims.

Pass criteria: system marks conflict and asks for resolution or selects newer/higher-confidence claim.

### 4. Supersession

Old fact is replaced by a newer fact.

Pass criteria: old claim becomes superseded, not deleted.

### 5. Non-keyword graph retrieval

Ask about downstream impact without using exact entity names.

Pass criteria: graph traversal finds connected claims/entities.

### 6. Secret redaction

Ingest text with token-like values.

Pass criteria: secrets are redacted and audit log records redaction.

### 7. Multi-agent conflict

Two agents update the same decision differently.

Pass criteria: conflict is detected and destructive overwrite is avoided.

### 8. Source invalidation

A source is marked stale or removed.

Pass criteria: dependent claims are downgraded or flagged.

### 9. Large document chunking

Ingest a long document.

Pass criteria: meaningful sections become evidence-backed claims, not one huge summary.

### 10. Markdown quality

Generated wiki pages should be useful to humans.

Pass criteria: page has summary, evidence links, related pages, current status, and open questions.

## Baseline fixtures

The repo includes small conformance fixtures under `examples/level-0/`, `examples/level-1/`, and `examples/level-3/`. These are not performance benchmarks. They are compatibility fixtures for future benchmark and adapter testing.

Benchmark scenario fixtures live under `benchmarks/fixtures/`.

For authoring rules and review criteria, see `docs/BENCHMARK_FIXTURE_AUTHORING.md`.

Run deterministic fixture scoring with:

```bash
make benchmark-score
```

Run real AKBP retrieval scoring with:

```bash
make benchmark
```

Run the focused adapter quality gate with:

```bash
make adapter-quality
```

The first runner validates scenario shape, citations, relation targets, supersession links, tool-server request ids, and fake-secret safety. `make benchmark-score` runs deterministic `--score` mode, which checks expected retrieval, citations, conflict flags, supersession behavior, dry-run/apply/rejection coverage, and safe-secret outcomes against fixture data.

`make benchmark` runs `--akbp` mode. This populates a temporary AKBP knowledge base from each fixture, checks real `akbp query` and `akbp context` retrieval against expected claim ids, and executes declared JSONL tool-server requests to validate write-apply, dry-run review, approval-rejection response shapes, plus optional `expected_result_schema` and `expected_error_schema` conformance against `schemas/tool-response.schema.json` defs. Requests can also use `expected_result_contains` and `expected_error_contains` with paths like `entities[].id` or `type_errors[]` to assert nested result or error-detail values. Escape literal dots in object keys with `\\.`, for example `methods.akbp\\.search.params_schema`.

`make adapter-quality` runs `python3 benchmarks/run_benchmarks.py --profile adapter-quality --akbp`. Use that smaller gate while developing an adapter: it executes only fixtures tagged for adapter output quality, then still uses the real CLI, JSONL tool server, response schemas, nested field checks, and approval-error checks.

When a fixture builds the local index, `akbp context` uses the same SQLite FTS5 retrieval path as `akbp search`. The older term-overlap retrieval remains only as an unindexed fallback. This keeps the public benchmark from accidentally measuring a weaker path than the tool server advertises.

Initial scenarios:

- `preference-recall`: recall a durable preference with citation.
- `supersession`: prefer a newer claim while preserving the superseded claim.
- `contradiction`: retrieve conflicting claims and ask for resolution.
- `correction-resolution`: apply newer corrections while preserving old conflicting knowledge until explicit resolution.
- `import-safety`: validate imported JSONL objects, schema-backed normal and strict `akbp.import_check` output, and rejected `akbp.import_apply` preview result shapes before durable writes.
- `invalid-param-rejection`: validate schema-backed `invalid_params` details for unknown, missing, wrong-typed, wrong item-typed, out-of-range, and unsupported enum method parameters before CLI execution.
- `import-apply-flow`: validate schema-backed `akbp.import_apply` dry-run previews and approval-gated apply results before durable writes.
- `import-apply-malformed`: validate schema-backed `akbp.import_apply` failure results for malformed JSONL before durable writes.
- `import-apply-skipped-existing`: validate import apply reports existing source and claim records through `skipped_existing` instead of rewriting them.
- `graph-jsonl-records`: populate real JSONL entities and relations and validate schema-backed export.
- `multi-agent-handoff`: retrieve cited prior-agent context before continuing adapter work.
- `review-gated-writes`: require agents to honor `review_required` and `apply_instruction` before applying durable writes, with real dry-run JSONL outputs.
- `read-method-schema`: verify read-only JSONL methods, including capability discovery and audit, return schema-backed response shapes without write approval, including advertised enforcement flags and method schema references.
- `search-index-observability`: verify safe prefix search and incremental index document-key observability through JSONL tool calls.
- `write-preview-crystallize-schema`: verify ingest dry-run previews, approved ingest, and approved session crystallization return schema-backed results.
- `approved-write-apply`: verify approved write methods return inspectable claim, source, or relation records.
- `unapproved-write-rejection`: verify non-dry-run writes, including import apply, without `approved:true` return structured `approval_required` errors.
- `adapter-structured-output-harness`: verify an adapter quality gate can machine-check capability negotiation, doctor/security posture, bounded startup context, dry-run preview metadata, and `approval_required` write rejection before trusting memory.
- `secret-safety`: redact or reject secret-like values before durable writes.
- `session-crystallization`: retrieve workflow claims from structured coding-agent sessions with citations.
