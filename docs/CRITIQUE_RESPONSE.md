# Critique response

AKBP should improve by treating skeptical feedback as product input, not by arguing over labels.

This note converts the main public critiques around LLM Wiki style systems and AKBP into repo work. It intentionally avoids claiming a research breakthrough. AKBP is a local-first protocol and reference implementation for durable, cited agent knowledge.

## What the critique got right

| Critique | Current reading | Repo response |
|---|---|---|
| A markdown `index.md` does not scale by itself. | Valid. A human index is useful, but it cannot be the only retrieval path once a KB grows. | Keep markdown as source-of-truth synthesis, but use rebuildable SQLite FTS5 for `search` and `context`. Benchmark fixtures now include search query compatibility and index observability. |
| Toy keyword retrieval is not enough proof. | Valid. Basic term overlap is useful as a fallback, not as the main proof of memory quality. | `akbp context` now uses the SQLite FTS5 index when present, matching `akbp search`; fallback keyword retrieval remains only for unindexed KBs. |
| Confidence, contradiction, and staleness rules can become vague. | Valid. These need explicit lifecycle states and examples, not just prose. | Claims carry status, confidence, supersession, contradiction, and source verification paths. Existing fixtures cover supersession, contradiction, correction, source verification, and write approval. |
| Large source ingest needs scaffolding before memory writes. | Valid. One giant summary is not durable knowledge. | Keep ingest review-gated. Prefer source registration, section-level claims, citations, and later crystallization. Large-document chunking remains a benchmark target before 1.0. |
| Provenance and auditability matter more than memory hype. | Strongly valid. | AKBP should continue emphasizing source ids, source hashes, citations, audit events, export manifests, and conformance checks. |
| Claims need measured repeated-session improvement. | Valid and still not fully solved. | The benchmark runner exercises repeated-session recall scenarios, but larger quality benchmarks and real adapter dogfooding remain 1.0 blockers. |
| Adoption is not proof yet. | Valid. | Keep public language as alpha protocol scaffolding. Do not imply mature ecosystem or production readiness. |
| Grep beat vector retrieval on a long-memory sample, and tool-output presentation changed scores even with identical retrieved evidence (Sen et al., *Is Grep All You Need? How Agent Harnesses Reshape Agentic Search*, arXiv:2605.15184). | Valid; presentation is part of the protocol surface, not a UI concern. | `akbp.search` and `akbp.context` accept an `output_mode` parameter. `inline` is default; `file` writes a grep-friendly JSONL artifact with sha256, byte size, and line count, and returns only an envelope. Schemas, the tool contract, and a `tool-output-presentation` benchmark fixture cover both shapes. Full position: `docs/HARNESS_AND_PRESENTATION.md`. |

## Positioning rules

Use:

- local-first protocol for durable, cited agent knowledge
- Git-like file artifacts for agent memory
- review-gated consistency layer for projects and agents
- portable substrate under CLIs, tool servers, IDE agents, and custom runtimes

Avoid:

- breakthrough AI memory
- magic memory
- production-ready memory platform
- vector database replacement
- autonomous knowledge understanding

## Engineering changes this implies

### Retrieval

- `akbp search` and `akbp context` must share the same indexed retrieval path when `.akbp/state.db` exists.
- Keyword overlap can remain only as an unindexed fallback.
- Search output should keep reporting the backend so tests and adapters know what path ran.
- Benchmark fixtures should keep adding ambiguous, noisy, stale, and multi-hop retrieval cases.

### Ingest and source handling

- Prefer `source add` and `source verify` before durable claims.
- Ingest should produce small claims with evidence, not bulk summaries.
- For long documents, future work should add chunk or section records with locators and hashes.

### Lifecycle and governance

- Contradictions should be represented, not silently resolved.
- Superseded claims should remain visible and cited.
- Approval-gated writes should remain the default for tool-server integrations.
- Source drift should downgrade confidence or force review in future implementations.

### Proof before bigger claims

AKBP should not claim strong memory quality until it shows:

1. repeated-session task improvement over repository instruction files plus plain markdown search,
2. retrieval precision and citation quality on larger fixtures,
3. stale-source and contradiction handling under realistic updates,
4. adapter use across more than one runtime,
5. migration/versioning behavior across bundle revisions.

## Practical next work

1. Add larger retrieval fixtures with noisy evidence and expected citation ids.
2. Add a long-document ingest fixture where section-level claims are required.
3. Add source-drift behavior beyond reporting changed hashes.
4. Add benchmark output that compares indexed retrieval against fallback keyword retrieval.
5. Add adapter examples that prove a new session retrieves old decisions without hidden chat history.
