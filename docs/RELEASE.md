# Release Readiness

Use this checklist before tagging or announcing an AKBP release.

## Version scope

A release should identify:

- protocol draft version
- reference CLI version
- supported conformance levels
- supported JSONL tool-server methods
- known limitations

Current release-candidate scope:

- protocol draft: initial public draft
- reference CLI version: `0.1.0` from `pyproject.toml`
- supported conformance levels: Level 0 through Level 3
- JSONL tool server: local stdio JSONL request/response server
- package status: alpha

## Required local checks

Run the full verification set from the repository root:

```bash
make validate
```

This expands to:

```bash
make guard
make test
make smoke
make benchmark-score
make benchmark
make install-smoke
```

Expected result:

- public reference guard passes
- unit and conformance tests pass
- CLI smoke flow passes
- benchmark fixtures pass deterministic scoring and real AKBP retrieval modes
- install smoke verifies packaged imports and CLI entrypoint
- source distribution manifest includes protocol docs, schemas, examples, adapters, and benchmark fixtures

## Manual sanity checks

Run the five-command quickstart from `README.md` in a temporary directory. Because ingest is preview-first for agents, review the `--dry-run` preview before applying imports.

Run the end-to-end example:

```bash
python3 cli/akbp.py --path examples/end-to-end-agent-flow conformance --level 3
python3 cli/akbp.py --path examples/end-to-end-agent-flow query "database migrations rollback"
python3 cli/akbp.py --path examples/end-to-end-agent-flow context "prepare migration release"
```

Run the JSONL tool server examples from `docs/TOOL_CONTRACT.md`, starting write-capable examples with request-level `dry_run: true` before applying writes.

## Artifact sanity checks

Before tagging, inspect the repository layout in `README.md` and make sure documented directories match tracked paths. Current adapter directories are:

- `adapters/coding-agent-template/`
- `adapters/example-coding-agent/`
- `adapters/terminal-coding-agent/`
- `adapters/editor-coding-agent/`

Current benchmark fixtures live under `benchmarks/fixtures/`, not a generated local benchmark output directory.

## Public repo guardrails

Before tagging:

- schema `$id` values must resolve to GitHub raw URLs
- public docs must avoid non-resolving future domains
- markdown docs must start with `# `
- generated local indexes, build artifacts, and temporary reports must stay out of git
- `MANIFEST.in` includes release artifacts without pulling generated state or temporary files
- examples must not contain real secrets or realistic credential prefixes

## Release notes template

```markdown
# AKBP <version>

## Highlights

- 

## Protocol changes

- 

## Reference implementation changes

- 

## Compatibility

- Conformance levels:
- Tool-server methods:
- Python requirement:

## Validation

- `make validate`
- `make guard`
- `make test`
- `make smoke`
- `make benchmark-score`
- `make benchmark`
- `make install-smoke`

## Known limitations

- 
```

## Early contributor asks

Good first contributions:

- add small, evidence-backed example knowledge bases
- add adapter docs for more coding-agent environments using public-safe names
- improve benchmark scenarios
- improve import and redaction tests
- add optional retrieval backends without changing the portable artifact format
