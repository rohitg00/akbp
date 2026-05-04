# Changelog

## Unreleased

### Added

- Add Agent Knowledge Base Protocol draft with portable artifacts for wiki pages, claims, entities, relations, sources, audit events, context packs, and knowledge base cards.
- Add dependency-free Python reference CLI with init, remember, query, context, ingest, crystallize, source, cite, supersede, contradict, index, search, export, audit, lint, conformance, and status commands.
- Add JSONL local tool server with capability discovery, structured errors, method schema references for every supported method, dry-run write safety, approval-gated non-dry-run writes, ingest preview responses, and query/context/write/index/search/crystallize methods.
- Add JSON schemas for core AKBP records, context packs, tool request/response envelopes, and tool method parameters.
- Add conformance checks through Level 3, covering file convention, structured claims/evidence, retrieval/context packs, and lifecycle relations.
- Add SQLite FTS5 local search with incremental indexing, stale entry cleanup, safe query sanitization, and automatic index refresh after write commands when state exists.
- Add safe local file ingest with common credential redaction, source records, imported wiki pages, lightweight signal extraction, optional claim creation, claim-text redaction, and dry-run previews.
- Add conservative transcript crystallization for decisions, actions, blockers, preferences, questions, and touched files with citations, duplicate skipping, preview-first CLI flow, and JSONL tool-server access.
- Add benchmark fixtures and runner for preference recall, supersession, contradiction handling, correction resolution, multi-agent handoff, import safety, review-gated writes, approved write apply outputs, unapproved write rejections, secret-safety, real AKBP retrieval checks, and JSONL tool-server response checks.
- Add examples for Level 0, Level 1, Level 3 lifecycle records, coding-agent flow, research/personal templates, end-to-end agent workflow, and JSONL tool-server approval flow.
- Add adapter templates and docs for runtime-neutral coding-agent startup, retrieval, write, ingest, index, and citation loops.
- Add install, schema, benchmark, tool contract, agent flow, release readiness, and release notes draft documentation.

### Validation

- Current release-candidate validation uses `make validate`, which runs `make guard`, `make test`, `make smoke`, `make benchmark-score`, `make benchmark`, and `make install-smoke`.

## 2026-04-29 draft

- Initial AKBP draft specification.
- Define portable artifacts: wiki pages, claims, entities, relations, sources, audit log, and local engine state.
- Define claim lifecycle states, retrieval contract, agent hooks, and conformance levels.
