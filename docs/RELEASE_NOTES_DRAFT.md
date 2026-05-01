# AKBP Release Notes Draft

This draft captures the current protocol and reference implementation state for an initial public release.

## Highlights

- Introduces Agent Knowledge Base Protocol as a portable convention for durable agent knowledge.
- Defines a local-first knowledge base layout with `AKBP.md`, `akbp.json`, markdown wiki pages, JSONL claims, graph records, source records, and audit history.
- Ships a dependency-free Python reference CLI and JSONL local tool server.
- Adds conformance checks through Level 3: file convention, structured claims, retrieval/context packs, and lifecycle relations.
- Adds examples and benchmark fixtures covering preference recall, supersession, contradiction handling, secret-safety, and end-to-end agent flow.

## Protocol surface

Current public artifacts include:

- `SPEC.md`
- `spec/latest.md`
- `schemas/*.schema.json`
- `docs/SCHEMAS.md`
- `docs/TOOL_CONTRACT.md`
- `docs/AGENT_FLOW.md`
- `docs/RELEASE.md`

Current schema coverage includes:

- claims
- entities
- relations
- evidence
- sources
- pages
- audit events
- context packs
- knowledge base cards
- JSONL tool request/response envelopes
- JSONL tool method parameters

## Reference CLI

The CLI currently supports:

- `init`
- `remember`
- `query`
- `context`
- `ingest`
- `crystallize`
- `source add`
- `cite`
- `supersede`
- `contradict`
- `index`
- `search`
- `export`
- `audit`
- `lint`
- `conformance`
- `status`

## JSONL local tool server

The local tool server currently supports:

- `akbp.capabilities`
- `akbp.status`
- `akbp.query`
- `akbp.context`
- `akbp.index`
- `akbp.search`
- `akbp.remember`
- `akbp.ingest`
- `akbp.conformance`
- `akbp.export`
- `akbp.audit`
- `akbp.cite`
- `akbp.source.add`
- `akbp.supersede`
- `akbp.contradict`

It includes capability discovery, schema references, structured errors, dry-run write support, and local search/index tools.

## Examples and benchmarks

Included examples:

- `examples/level-0/`
- `examples/level-1/`
- `examples/level-3/`
- `examples/end-to-end-agent-flow/`
- `examples/coding-agent/`
- `examples/research/`
- `examples/personal/`

Included benchmark fixtures:

- preference recall
- supersession
- contradiction
- secret safety

The benchmark runner validates fixture shape and can populate a temporary AKBP knowledge base to check real `query` and `context` retrieval behavior.

## Validation for this release candidate

Run before tagging:

```bash
make guard
make test
make smoke
make benchmark
make install-smoke
```

## Known limitations

- Retrieval is keyword and SQLite FTS5 only for now.
- Vector search is not included yet.
- Hosted docs are not available yet.
- Cross-device sync is specified as a future protocol area, not implemented in the reference CLI.
- Crystallization is deliberately conservative and local.
- Ingest is local-file oriented and does not fetch remote sources.

## Suggested announcement angle

Agents should not start every session with amnesia.

AKBP is the portable knowledge layer for agents: files humans can inspect, JSONL agents can update, citations systems can trust, and conformance tests implementations can share.
