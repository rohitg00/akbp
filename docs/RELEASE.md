# Release Readiness

Use this checklist before tagging or announcing an AKBP release.

## Version scope

A release should identify:

- protocol draft version
- reference CLI version
- supported conformance levels
- supported JSONL tool-server methods
- known limitations

## Required local checks

Run the full verification set from the repository root:

```bash
make guard
make test
make smoke
make benchmark
make install-smoke
```

Expected result:

- public reference guard passes
- unit and conformance tests pass
- CLI smoke flow passes
- benchmark fixtures pass in real AKBP retrieval mode
- install smoke verifies packaged imports and CLI entrypoint

## Manual sanity checks

Run the five-command quickstart from `README.md` in a temporary directory.

Run the end-to-end example:

```bash
python3 cli/akbp.py --path examples/end-to-end-agent-flow conformance --level 3
python3 cli/akbp.py --path examples/end-to-end-agent-flow query "database migrations rollback"
python3 cli/akbp.py --path examples/end-to-end-agent-flow context "prepare migration release"
```

Run the JSONL tool server examples from `docs/TOOL_CONTRACT.md`.

## Public repo guardrails

Before tagging:

- schema `$id` values must resolve to GitHub raw URLs
- public docs must avoid non-resolving future domains
- markdown docs must start with `# `
- generated local indexes, build artifacts, and temporary reports must stay out of git
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

- `make guard`
- `make test`
- `make smoke`
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
