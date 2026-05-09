# AKBP Release Notes Draft

This draft captures the current protocol and reference implementation state for an initial public release.

Release candidate scope:

- protocol draft: initial public draft
- reference CLI version: `0.1.0`
- conformance: Level 0 through Level 3
- package status: alpha

## Highlights

- Introduces Agent Knowledge Base Protocol as a portable convention for durable agent knowledge.
- Defines a local-first knowledge base layout with `AKBP.md`, `akbp.json`, markdown wiki pages, JSONL claims, graph records, source records, and audit history.
- Ships a dependency-free Python reference CLI and JSONL local tool server.
- Adds conformance checks through Level 3: file convention, structured claims, retrieval/context packs, and lifecycle relations.
- Adds examples and benchmark fixtures covering preference recall, supersession, contradiction handling, correction resolution, multi-agent handoff, import safety, import apply success/failure/skipped-record flows, invalid parameter rejections, review-gated writes, approved write apply outputs, unapproved write rejections, secret-safety, and end-to-end agent flow.

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
- `akbp.import_check`
- `akbp.import_apply`
- `akbp.conformance`
- `akbp.export`
- `akbp.audit`
- `akbp.cite`
- `akbp.source.add`
- `akbp.supersede`
- `akbp.contradict`
- `akbp.crystallize_session`

It includes capability discovery, schema references for every supported method, advertised parameter-schema enforcement features, structured errors, schema-backed invalid JSON errors that do not echo raw input, schema-backed invalid parameter errors for unknown, missing, wrong-typed, wrong item-typed, bounded evidence/entity arrays, out-of-range, and unsupported enum params, schema-backed CLI and internal failure details, dry-run write support, `review_required` metadata, `apply_instruction` guidance, approval-gated non-dry-run writes with `approved:true`, ingest dry-run preview responses, approved ingest result responses, schema-backed JSONL import checks with accepted, rejected, and error counts plus strict failure gates, review-gated JSONL import apply for source and claim records through the CLI and JSONL server, schema-backed import-apply failure shapes for rejected and malformed JSONL exports, skipped-existing reporting for duplicate imports, write-safety guidance, local search/index tools, and transcript crystallization through the JSONL server.

## Examples and benchmarks

Included examples:

- `examples/level-0/`
- `examples/level-1/`
- `examples/level-3/`
- `examples/end-to-end-agent-flow/`
- `examples/tool-server-approval-flow/`
- `examples/adapter-lifecycle/`
- `examples/coding-agent/`
- `examples/research/`
- `examples/personal/`
- `adapters/coding-agent-template/`
- `adapters/example-coding-agent/`
- `adapters/terminal-coding-agent/`
- `adapters/editor-coding-agent/`

Included benchmark fixtures:

- preference recall
- supersession
- contradiction
- correction resolution
- import safety
- import compatibility edges
- import apply flow
- import apply malformed JSONL
- import apply skipped existing records
- export bundle compatibility
- graph JSONL records
- invalid parameter rejections
- multi-agent handoff
- retrieval citation bundle
- retrieval ambiguity ranking
- retrieval noisy evidence
- search index observability
- search query compatibility
- review-gated writes
- approved write apply outputs
- unapproved write rejections
- adapter session operation
- adapter write safety
- read method schema
- unknown method rejection
- capability negotiation
- secret safety
- session crystallization
- write preview crystallize schema

The benchmark runner validates fixture shape and can populate a temporary AKBP knowledge base to check real `query` and `context` retrieval behavior across the fixture set. Fixtures can also execute JSONL tool-server requests to verify dry-run review metadata, approved write result records, import-apply failure/skipped-existing result shapes, search/index observability, empty FTS query behavior, retrieval/citation bundles, adapter lifecycle operations, `invalid_params` rejection details for type, bounded array-item count and length, range, and enum checks, and `approval_required` rejection details. The install smoke flow now exercises the installed JSONL tool-server entrypoint, including capability discovery and schema-backed invalid-param output.

## Validation for this release candidate

Run before tagging:

```bash
make validate

# expands to:
make guard
make test
make smoke
make benchmark-score
make benchmark
make install-smoke
```

## Known limitations

- Retrieval is keyword and SQLite FTS5 only for now.
- Vector search is not included yet.
- Hosted docs are not available yet.
- Cross-device sync is specified as a future protocol area, not implemented in the reference CLI.
- Crystallization is deliberately conservative and local.
- Ingest is local-file oriented and does not fetch remote sources. It now supports dry-run previews and redacts imported pages plus optional claim text before durable writes.
- Adapter coverage is intentionally runtime-neutral first; runtime-specific adapters should start from the public template and example fixture.

## Suggested announcement angle

Agents should not start every session with amnesia.

AKBP is the portable knowledge layer for agents: files humans can inspect, JSONL agents can update, citations systems can trust, and conformance tests implementations can share.
