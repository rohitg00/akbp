# Changelog

## Unreleased

- Added a runnable structured output harness example for adapter authors, including validation for JSONL envelopes, capability negotiation, cited startup context, dry-run review metadata, and approval-gated write rejection.
- Added machine-readable local-first runtime requirements to generated client configs so adapter installers can surface no-cloud, no-network, no-secret setup boundaries before enabling trust.
- Added a runnable JSONL quickstart example that verifies the canonical tool-server adoption sequence from capability discovery through reviewed write, cited recall, and portable export.
- Added an adapter structured-output harness benchmark fixture for capability negotiation, doctor/security posture, bounded startup context, dry-run preview metadata, and approval-gated write rejection.
- Added a runnable adapter lifecycle example that verifies capability negotiation, session-start retrieval, session-end dry-run review, unapproved write rejection, approved apply, index refresh, and recalled context.
- Expanded generated client configs so reviewed-write bridges advertise ingest preview and approved index refresh wrappers, while blocking every direct write method by default.
- Added inherited-repo intake guidance and a benchmark fixture so unfamiliar repository handoffs require discovery, doctor readiness, cited startup context, and read-only defaults before durable writes.

### Added

- Add Agent Knowledge Base Protocol draft with portable artifacts for wiki pages, claims, entities, relations, sources, audit events, context packs, and knowledge base cards.
- Add dependency-free Python reference CLI with init, remember, query, context, ingest, crystallize, source, cite, supersede, contradict, index, search, export, audit, lint, conformance, and status commands.
- Add JSONL local tool server with capability discovery, advertised parameter-schema enforcement features, structured errors, schema-backed invalid JSON handling, schema-backed invalid parameter errors for type, bounded array-item count and length, range, and enum checks, schema-backed CLI and internal failure details, method schema references for every supported method, dry-run write safety, import-apply dry-run review metadata, schema-shaped import-apply missing-file failures, approval-gated non-dry-run writes, ingest preview responses, and query/context/write/index/search/crystallize methods.
- Add capability runtime reporting for method-schema parity errors so adapters can detect schema/runtime drift.
- Add JSON schemas for core AKBP records, context packs, tool request/response envelopes, and tool method parameters.
- Add conformance checks through Level 3, covering file convention, structured claims/evidence, retrieval/context packs, and lifecycle relations.
- Add SQLite FTS5 local search with incremental indexing, stale entry cleanup, safe query sanitization, dotted method-name query preservation, and automatic index refresh after write commands when state exists.
- Use the SQLite FTS5 index for context retrieval when the local index exists, keeping term-overlap retrieval as an unindexed fallback.
- Add safe local file ingest with common credential redaction, source records, imported wiki pages, lightweight signal extraction, optional claim creation, claim-text redaction, and dry-run previews.
- Add conservative transcript crystallization for decisions, actions, blockers, preferences, questions, and touched files with citations, duplicate skipping, preview-first CLI flow, and JSONL tool-server access.
- Add benchmark fixtures and runner for preference recall, supersession, contradiction handling, correction resolution, multi-agent handoff, git-native agent handoff, import safety, import apply success/failure/skipped-record flows, duplicate import-id rejection, invalid parameter rejections, review-gated writes, approved write apply outputs, unapproved write rejections, secret-safety, real AKBP retrieval checks, and JSONL tool-server response checks.
- Add examples for Level 0, Level 1, Level 3 lifecycle records, coding-agent flow, git-native agent handoff, research/personal templates, end-to-end agent workflow, and JSONL tool-server approval flow.
- Add adapter templates and docs for runtime-neutral coding-agent startup, retrieval, write, ingest, index, citation loops, and `akbp.session.start` / `akbp.session.end` lifecycle wiring.
- Add a public-safe git-native agent adapter template for repo-backed agent runtimes.
- Add adapter author guidance for startup capability gates and a preview-approval-apply write state machine.
- Add install, schema, benchmark, tool contract, agent flow, critique response, release readiness, and release notes draft documentation, including installed JSONL tool-server smoke coverage.

### Validation

- Current release-candidate validation uses `make validate`, which runs `make guard`, `make test`, `make smoke`, `make benchmark-score`, `make benchmark`, and `make install-smoke`.

## 2026-04-29 draft

- Initial AKBP draft specification.
- Define portable artifacts: wiki pages, claims, entities, relations, sources, audit log, and local engine state.
- Define claim lifecycle states, retrieval contract, agent hooks, and conformance levels.
