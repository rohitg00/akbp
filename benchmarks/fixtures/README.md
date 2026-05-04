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
- `expected_error_code`: structured error code expected for rejected requests
- `expected_error_fields`: fields that must exist in structured `error.details`
- `expected_error_values`: exact values that must match in structured `error.details`

Any field checked in `expected_result_values` or `expected_error_values` must also be listed in the corresponding field list, so fixtures document the complete contract they validate.

## Current fixtures

- `adapter-write-safety`: require runtime adapters to share the same dry-run, review metadata, approved write, and privacy boundary.
- `preference-recall`: recall a durable user preference with evidence.
- `supersession`: prefer a newer claim while preserving the old claim.
- `contradiction`: detect conflicting claims and require resolution.
- `correction-resolution`: prefer a newer correction while preserving old conflicting knowledge until explicit resolution.
- `secret-safety`: reject or redact secret-like text before durable writes.
- `import-safety`: validate JSONL import objects for redaction or rejection before durable writes.
- `session-crystallization`: retrieve workflow claims from a structured coding-agent session with citations.
- `multi-agent-handoff`: retrieve cited context from prior agent sessions before continuing adapter work.
- `review-gated-writes`: require agents to honor dry-run review metadata before applying durable writes.
- `approved-write-apply`: verify approved JSONL write calls return concrete records that adapters can inspect after approval.
- `unapproved-write-rejection`: verify non-dry-run JSONL writes without `approved:true` return structured `approval_required` errors.
