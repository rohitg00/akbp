# Benchmark Fixture Authoring Guide

Use this guide when adding AKBP benchmark scenarios under `benchmarks/fixtures/`.

## Required shape

Each scenario lives in its own directory and uses `scenario.json` as the entrypoint.

Required top-level fields:

- `id`: stable scenario id. Use a version or sequence suffix when you need to introduce a non-breaking variant.
- `task`: what the agent runtime must prove.
- `setup`: records, imports, or JSONL tool-server requests used by the fixture.
- `query`: retrieval task or runtime prompt.
- `expected`: pass criteria checked by the deterministic and real AKBP runners.

## Evidence-backed retrieval fixtures

For retrieval scenarios:

- include at least one `setup.sources[]` record with a stable id.
- cite source ids from `setup.claims[].evidence`.
- use `expected.must_retrieve` for claim ids that must appear in query or context output.
- use `expected.must_cite` when deterministic scoring must verify evidence ids.
- use `expected.must_cite_in_context` when real context output must include evidence citations.

## Tool-server fixtures

For JSONL tool-server scenarios:

- put requests in `setup.tool_server_requests[]`.
- give every request a stable `id`.
- use `expected_result_schema` or `expected_error_schema` for schema-backed responses.
- use `expected_result_fields` or `expected_error_fields` for required response keys.
- use `expected_result_contains` or `expected_error_contains` for nested values.
- escape literal dots in object keys with `\\.`, for example `methods.akbp\\.search.params_schema`.

## Write-safety fixtures

For write-capable methods:

- include a dry-run request before any approved apply request.
- assert `review_required` and `apply_instruction` in preview responses when applicable.
- assert `approval_required` errors for non-dry-run writes without request-level `approved:true`.
- do not add realistic secrets, private paths, or raw private logs to fixtures.

## Validation checklist

Before opening a PR:

```bash
python3 benchmarks/run_benchmarks.py --score
python3 benchmarks/run_benchmarks.py --akbp
make guard
make test
make smoke
make install-smoke
```

Also add the scenario directory to `benchmarks/fixtures/README.md` so fixture inventory tests stay useful.
