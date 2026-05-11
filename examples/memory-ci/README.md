# Memory CI example

This example shows how a project can enforce AKBP quality gates in CI.

Use it as a starting point for a GitHub Actions workflow or any local CI system.

## Run

From the repository root:

```bash
examples/memory-ci/run.sh
```

Expected success marker:

```text
AKBP memory CI example passed
```

## Gates

A practical memory CI job should run:

```bash
akbp --path ./kb lint
akbp --path ./kb source verify --fail-on-issue
akbp --path ./kb conformance --level 2
akbp --path ./kb export --output akbp-bundle.json
akbp --path ./kb export-check akbp-bundle.json --fail-on-issues
```

For external JSONL proposals, add:

```bash
akbp --path ./kb import-check incoming.jsonl --fail-on-rejected
akbp --path ./kb import-apply incoming.jsonl --dry-run
```

Apply only after review:

```bash
akbp --path ./kb import-apply incoming.jsonl --approved
```

## Example GitHub Actions job

```yaml
name: Memory CI

on:
  pull_request:
  push:
    branches: [main]

jobs:
  akbp-memory:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install AKBP
        run: python -m pip install .
      - name: Validate project memory
        run: |
          akbp --path ./kb lint
          akbp --path ./kb source verify --fail-on-issue
          akbp --path ./kb conformance --level 2
          akbp --path ./kb export --output akbp-bundle.json
          akbp --path ./kb export-check akbp-bundle.json --fail-on-issues
```

## Why this matters

Memory should not silently rot. CI gives teams a visible gate for stale sources, invalid bundles, broken conformance, and unsafe imported knowledge.
