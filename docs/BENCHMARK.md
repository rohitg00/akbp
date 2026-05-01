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

The repo includes small conformance fixtures under `examples/level-0/` and `examples/level-1/`. These are not performance benchmarks. They are compatibility fixtures for future benchmark and adapter testing.

Benchmark scenario fixtures live under `benchmarks/fixtures/`.

Run fixture validation with:

```bash
make benchmark
```

The first runner validates scenario shape, citations, relation targets, supersession links, and fake-secret safety. It also has a deterministic `--score` mode that checks expected retrieval, citations, conflict flags, supersession behavior, and safe-secret outcomes against fixture data.

Initial scenarios:

- `preference-recall`: recall a durable preference with citation.
- `supersession`: prefer a newer claim while preserving the superseded claim.
- `contradiction`: retrieve conflicting claims and ask for resolution.
- `secret-safety`: redact or reject secret-like values before durable writes.
