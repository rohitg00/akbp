# AKBP Benchmark

## Purpose

AKBP needs an evaluation harness so the protocol does not become vibes.

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

Run deterministic fixture scoring with:

```bash
make benchmark-score
```

Run real AKBP retrieval scoring with:

```bash
make benchmark
```

The first runner validates scenario shape, citations, relation targets, supersession links, tool-server request ids, and fake-secret safety. `make benchmark-score` runs deterministic `--score` mode, which checks expected retrieval, citations, conflict flags, supersession behavior, dry-run/apply/rejection coverage, and safe-secret outcomes against fixture data.

`make benchmark` runs `--akbp` mode. This populates a temporary AKBP knowledge base from each fixture, checks real `akbp query` and `akbp context` retrieval against expected claim ids, and executes declared JSONL tool-server requests to validate write-apply, dry-run review, approval-rejection response shapes, plus optional `expected_result_schema` and `expected_error_schema` conformance against `schemas/tool-response.schema.json` defs.

Initial scenarios:

- `preference-recall`: recall a durable preference with citation.
- `supersession`: prefer a newer claim while preserving the superseded claim.
- `contradiction`: retrieve conflicting claims and ask for resolution.
- `correction-resolution`: apply newer corrections while preserving old conflicting knowledge until explicit resolution.
- `import-safety`: validate imported JSONL objects and redaction before durable writes.
- `multi-agent-handoff`: retrieve cited prior-agent context before continuing adapter work.
- `review-gated-writes`: require agents to honor `review_required` and `apply_instruction` before applying durable writes, with real dry-run JSONL outputs.
- `read-method-schema`: verify read-only JSONL methods, including capability discovery and audit, return schema-backed response shapes without write approval.
- `search-index-observability`: verify safe prefix search and incremental index document-key observability through JSONL tool calls.
- `write-preview-crystallize-schema`: verify ingest dry-run previews, approved ingest, and approved session crystallization return schema-backed results.
- `approved-write-apply`: verify approved write methods return inspectable claim, source, or relation records.
- `unapproved-write-rejection`: verify non-dry-run writes without `approved:true` return structured `approval_required` errors.
- `secret-safety`: redact or reject secret-like values before durable writes.
- `session-crystallization`: retrieve workflow claims from structured coding-agent sessions with citations.
