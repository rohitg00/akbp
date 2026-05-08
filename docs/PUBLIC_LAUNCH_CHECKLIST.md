# Public launch checklist

Use this checklist before marketing AKBP outside a private engineering loop. It is intentionally stricter than a normal local release checklist because AKBP handles durable agent memory.

## Positioning gate

Before announcing:

- say `alpha`, not `1.0`, `production-ready`, or `full compatibility`
- describe AKBP as a durable knowledge protocol and reference implementation
- keep claims tied to shipped behavior, tests, examples, schemas, fixtures, and CI
- avoid comparing AKBP as a full replacement for larger agent runtimes
- link to demo, adapter author quickstart, tool contract, security model, and release notes

## Engineering gate

Required local validation from a clean checkout:

```bash
make guard
make test
make smoke
make install-smoke
python3 benchmarks/run_benchmarks.py --score --akbp
make validate
make build
```

Required remote validation:

- GitHub CI passes on Python 3.9, 3.10, 3.11, and 3.12
- package build passes
- automated review has no unresolved action items

## Security and privacy gate

Before public launch:

- read `SECURITY.md` and `docs/SECURITY_MODEL.md`
- confirm write-capable JSONL methods remain dry-run and approval gated
- confirm request-size limits and path validation are advertised in capabilities
- confirm ingest redacts source content, optional claim text, and source titles
- confirm import/export checks reject secret-like bundle values
- inspect examples, fixtures, screenshots, and docs for live secrets or private data

## Demo gate

The public demo path must work without private infrastructure:

```bash
make demo
```

The demo should show:

- initializing a knowledge base
- adding or ingesting reviewed knowledge
- indexing and searching
- retrieving context with citations
- JSONL tool-server dry-run before apply

## Docs gate

Before launch, verify these entry points are current:

- `README.md`
- `docs/ADAPTER_AUTHOR_QUICKSTART.md`
- `docs/TOOL_CONTRACT.md`
- `docs/ARCHITECTURE.md`
- `docs/SECURITY_MODEL.md`
- `docs/TROUBLESHOOTING.md`
- `docs/RELEASE.md`
- `docs/RELEASE_NOTES_DRAFT.md`

## Launch copy guardrails

Allowed:

- `AKBP is a public alpha for durable agent knowledge.`
- `The reference implementation ships CLI, JSONL tool server, schemas, fixtures, examples, and CI.`
- `Write flows are review-gated by default.`

Avoid:

- claiming broad runtime parity
- claiming mature enterprise production readiness
- claiming secret redaction is perfect
- implying hosted memory, vector database, or chat-history replacement
- using private benchmark names, private tool names, or copied positioning from other repos

## Post-launch monitoring

After launch:

- watch CI on incoming PRs
- watch security reports privately
- triage adapter feedback separately from protocol feedback
- turn real usage failures into small tests or benchmark fixtures
- keep public claims narrower than shipped behavior
