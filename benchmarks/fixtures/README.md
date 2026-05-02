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
- `setup`: sources, claims, and relations to ingest
- `query`: retrieval or maintenance question
- `expected`: pass criteria

## Current fixtures

- `preference-recall`: recall a durable user preference with evidence.
- `supersession`: prefer a newer claim while preserving the old claim.
- `contradiction`: detect conflicting claims and require resolution.
- `correction-resolution`: prefer a newer correction while preserving old conflicting knowledge until explicit resolution.
- `secret-safety`: reject or redact secret-like text before durable writes.
- `import-safety`: validate JSONL import objects for redaction or rejection before durable writes.
- `session-crystallization`: retrieve workflow claims from a structured coding-agent session with citations.
- `multi-agent-handoff`: retrieve cited context from prior agent sessions before continuing adapter work.
