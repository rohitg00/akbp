# Changelog

## Unreleased

- Added a compaction-survival claim gate to generated client configs so
  adapters must prove cited session-start recovery, surfaced warnings, budget
  diagnostics, and context-use reporting before claiming memory survives
  compaction or restart.
- Added a temporal graph claim gate to generated client configs so adapter
  installers can verify cited claims, lifecycle state, relation records,
  conformance, export-check, and graph benchmark output before trusting
  graph-backed memory claims.
- Added contested-claim warnings to query/context retrieval and a fail-closed
  benchmark fixture so adapters do not plan from disputed recalled memory.
- Added a local-first adoption probe check to the adoption preflight example so
  installer UIs prove the memory-server comparison contract before positioning
  AKBP as a trusted local project-memory layer.
- Added a cited startup gate to the adapter lifecycle example so runtime
  adapters prove trusted_for_planning before recalled context can shape a plan.
- Added a branch-scoped handoff gate to generated adapter configs so coding
  agents capture branch, worktree, commit, and cited source metadata without
  treating AKBP as the source of truth for Git state.
- Added a machine-readable tool-schema budget preflight gate to generated
  adapter configs so hosts fail closed before exposing over-broad AKBP tool
  surfaces.
- Added profile-specific host tool schema budgets to generated client configs
  so startup-context adapters expose only the minimal cited-recall tools before
  upgrading to broader read-only inspection.
- Added a local-first adoption probe to generated client configs so installer
  UIs can verify no-Docker/no-cloud setup, cited startup context, approval
  gating, and export-checkable artifacts before positioning AKBP against
  opaque memory servers.
- Added a memory feature-claim audit to generated client configs so adapter
  installers can verify semantic recall, graph memory, context-window savings,
  shared memory, and local-first safety claims before trusting recalled project
  knowledge or enabling writes.
- Added explicit context planning trust decisions to context quality payloads so
  adapters can branch on trusted_for_planning and fallback_reason instead of
  re-deriving remember/reject behavior from warnings, citations, and budget
  fields.
- Added a host auto-detect contract to discovery and generated client configs
  so installer probes stay inventory-only until users review exact host config
  diffs and preflight checks.
- Added inherited-repo takeover risk triage to discovery output so adapters can
  classify stale, uncited, or private prior memory before planning from it.
- Added a machine-readable external-memory promotion triage contract so adapter
  installers can classify memory-server rows before import-check or write
  preview.
- Added structured-output harness success markers to generated client configs
  so adapter installers can verify the setup gate without duplicating stdout
  marker lists.
- Added a source-of-truth drift benchmark fixture so adapter trust gates prove
  changed repository evidence blocks planning from recalled project memory.
- Tightened generated adapter startup trust gates so discovery, client configs,
  host-tool manifests, and verification plans request `fail_on_warnings:true`
  before recalled context can influence planning.
- Added first-run adoption triage to discovery output so installers can choose
  read-only recall, reviewed promotion, or scratch-only fallback based on
  citations, response preservation, and review-surface support.
- Tightened context budget schemas so adapter validators require clipped,
  omitted, and before/after item diagnostics whenever a budget object is
  returned.
- Added adapter response-contract validation to generated ten-minute proofs so
  installers run the structured-output harness before recalled memory can
  influence planning.
- Added an AKBP-vs-memory-server decision table to the adoption guide so users
  can keep fast runtime memory as scratchpad while promoting only cited,
  reviewed project facts into portable AKBP artifacts.
- Changed generated adapter startup preflight requests to require at least one
  cited context item, so hosts prove the citation gate in machine-readable
  config instead of relying only on prompt guidance.
- Added a compaction handoff recall benchmark fixture so adapter authors can
  prove cited, lifecycle-aware handoff snapshots beat stale relative-date memory
  before trusting recalled context after compaction.
- Added optional JSONL trace capture to the quickstart example so adapter
  authors can inspect exact request and response envelopes while preserving the
  normal pass/fail smoke output.
- Added an explicit `budget.truncated` boolean to context response budgets so
  adapter startup trust gates can fail closed on clipped or omitted recalled
  context without deriving state from item counts.
- Added a machine-readable startup trust gate to generated adapter prompt
  contracts so hosts can fail closed on empty, uncited, truncated, or
  unsurfaced-warning startup context before planning from recalled memory.
- Added a source provenance gate to generated adapter prompt contracts so
  reviewed-write adapters require source ids, cited evidence, or newly
  registered source material before previewing durable claims.
- Added a machine-readable ten-minute adoption proof to discovery and generated
  client configs so installers can prove local setup, cited recall,
  review-gated writes, and portable export before positioning AKBP as agent
  memory.
- Added a machine-readable session-memory boundary to tool-server capabilities
  and generated client config so adapters can distinguish runtime scratch from
  reviewed durable AKBP promotion.
- Added profile-aware JSONL doctor preflight checks so generated client configs
  can gate startup-context, read-only, and reviewed-write adapters against the
  selected readiness profile instead of forcing full adapter readiness.
- Blocked `import-apply` from writing uncited or non-source-backed claims even when `--approved` is passed, so migration/import flows must satisfy the review readiness gate before durable writes.
- Added a source verification attention summary so adapters can surface changed or missing evidence and affected claim ids before trusting recalled memory.
- Changed `source verify <source_id>` so unknown source ids fail as missing evidence instead of passing an empty verification check.
- Added `akbp context --fail-on-warnings` so adapter startup gates can fail closed on warning-bearing context such as source drift, inactive matches, empty retrieval, or budget truncation before trusting recalled memory.
- Added a schema-backed `knowledge_capability` descriptor to `akbp.capabilities` so tool hosts can classify AKBP as local, cited, review-gated agent knowledge before exposing it through tool-protocol or host-native memory surfaces.
- Added explicit task-scope requirements to the `knowledge_capability` retrieval descriptor so adapters know to pass a KB path plus bounded task or query before trusting startup context.
- Added machine-readable scope selection to generated client configs so adapter installers can distinguish repo-local, team-shared, personal-assistant, and migration knowledge-base boundaries before trusting recalled memory.
- Added executable preflight requests to generated host and client tool manifests so adapter installers can run capability negotiation, doctor, and bounded startup context checks without reconstructing JSONL calls from docs.
- Added a generated managed tool-host bridge contract so stdio-compatible hosts can launch AKBP with read-only tool exposure, preflight checks, structured response requirements, and explicit reviewed-write gating.
- Added descriptions and safety metadata to generated host-tool manifests so tool-protocol hosts can create read-only wrappers without guessing tool purpose or review requirements.
- Added a runnable structured output harness example for adapter authors, including validation for JSONL envelopes, capability negotiation, cited startup context, dry-run review metadata, and approval-gated write rejection.
- Added a runnable adoption preflight example that verifies first-run trust boundaries, cited startup context readiness, portable read-only client config, and unapproved write rejection.
- Expanded the adoption preflight example to verify nested `akbp discover` profile selection, adapter prompt contract, recommended harness, and ten-minute proof before host integration.
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
