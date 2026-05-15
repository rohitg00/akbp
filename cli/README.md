# AKBP CLI

Dependency-free reference CLI for AKBP.

## Install

Run directly from source:

```bash
python3 cli/akbp.py --help
```

Or install locally:

```bash
python3 -m pip install .
akbp --help
```

See `../docs/INSTALL.md` for the full install and smoke-test flow.

## Usage

```bash
python3 cli/akbp.py --path ./my-kb init --level 0
python3 cli/akbp.py --path ./my-kb remember "This project uses Bun instead of npm" --type decision --evidence README.md
python3 cli/akbp.py --path ./my-kb query "Bun npm"
python3 cli/akbp.py --path ./my-kb index
python3 cli/akbp.py --path ./my-kb index --incremental
python3 cli/akbp.py --path ./my-kb search "Bun npm"
python3 cli/akbp.py --path ./my-kb context "continue the package manager migration" --max-chars 4000
python3 cli/akbp.py --path ./my-kb/subdir discover
python3 cli/akbp.py --path ./my-kb cite claim_123
python3 cli/akbp.py --path ./my-kb supersede claim_123 "Use the stdlib CLI until package metadata exists" --type decision --evidence cli/akbp.py
python3 cli/akbp.py --path ./my-kb contradict claim_123 claim_456 --evidence source_123
python3 cli/akbp.py --path ./my-kb conformance --level 3
python3 cli/akbp.py --path ./my-kb ingest notes.md --claim "The project ships small verified batches." --claim-type decision
python3 cli/akbp.py --path ./my-kb crystallize transcript.md
python3 cli/akbp.py --path ./my-kb crystallize transcript.md --apply
python3 cli/akbp.py --path ./my-kb client-config --profile read-only
python3 cli/akbp.py --path ./my-kb lint
```

This implementation writes portable markdown and JSONL artifacts. It is intentionally small so other implementations can copy the behavior.

## Ingest

`akbp ingest notes.md` imports a local file into `wiki/imports/`, records a source in `raw/sources/sources.jsonl`, extracts lightweight signals from headings and decision-like lines, and redacts common token/key patterns from the imported page. Use `--claim` to create one evidence-backed claim while importing; claim text is redacted with the same safety filter before durable write. Use `akbp ingest notes.md --dry-run` to preview source, page, claim ids, signals, redaction status, and would-write paths without changing the knowledge base.

`akbp import-check export.jsonl` validates imported JSONL objects before durable writes. It reports accepted ids and rejected ids without echoing secret-like raw values, rejects claims that cite unknown `source_...` evidence ids, and lets agents review exports before using `ingest`, `remember`, or `import-apply`. Add `--fail-on-rejected` in automation when any rejected object should fail the gate.

`akbp import-apply export.jsonl --dry-run` previews accepted source and claim records that would be written. Apply with `akbp import-apply export.jsonl --approved` only after reviewing `import-check` and the dry-run output. Rejected, malformed, or unsupported objects block the apply path.

Import apply review checklist:

- Run `akbp import-check export.jsonl --fail-on-rejected` when automation must stop on any rejected object.
- Confirm `accepted_count`, `rejected_count`, and `error_count` before applying.
- Review `would_write.sources` and `would_write.claims` from the dry-run output.
- Do not apply when rejected objects, parse errors, unsupported kinds, or secret-like values appear.
- Treat `--approved` as the durable write boundary, not as a validation shortcut.

## Crystallize

`akbp crystallize transcript.md` previews extracted decisions, actions, blockers, preferences, questions, and file references without writing durable artifacts.

The extractor recognizes structured transcript sections such as `Decisions`, `Action Items`, `Blockers`, `Preferences`, and `Open Questions`. It also normalizes bullets, checkboxes, speaker prefixes, and labels such as `Blocker:` or `Question:` before proposing durable claims.

`akbp crystallize transcript.md --apply` turns the reviewed summary into:

- a session page under `wiki/sessions/`
- a transcript source record under `raw/sources/sources.jsonl`
- durable claims for detected decisions, actions, blockers, preferences, and questions

The extractor is deliberately conservative and local. Re-running the same crystallization skips duplicate claim IDs instead of appending the same memory again.

## Context packs

`akbp context` returns a protocol-shaped context pack for agents. It is the CLI equivalent of a local context retrieval call.

Use `--max-chars` when an adapter has a fixed startup prompt budget. The returned context pack includes a `budget` object with the requested cap, final summary characters, original summary characters, and the number of truncated or omitted items.

## Discovery

akbp discover finds the nearest akbp.json from --path or its parent directories and prints a JSON preflight payload for adapter installers. It reports the resolved KB path, card metadata, default scope, artifact presence, trust-boundary rules, AKBP's role relative to memory servers, repository instruction files, tool-protocol hosts, and search indexes, plus recommended doctor, client-config, and context commands.

Use it before wiring a runtime that starts from an arbitrary workspace subdirectory:

    python3 cli/akbp.py --path ./my-kb/subdir discover
    python3 cli/akbp.py --path ./my-kb/subdir discover | jq .trust_boundary
    python3 cli/akbp.py --path ./my-kb/subdir discover | jq .positioning

If no Knowledge Base Card is found, the command exits non-zero and suggests akbp init instead of inventing durable memory state.

## Client config

`akbp client-config` prints a pasteable stdio JSONL tool-server configuration for coding agents, editor agents, task runners, or local assistants.
The emitted config includes `runtime_requirements` so installers can tell users
up front that the reference stdio flow is local-first and does not require a
network connection, cloud account, or secrets.
It also includes `first_run_sequence`, an ordered setup path that resolves the
knowledge-base path, negotiates capabilities, checks doctor readiness, retrieves
cited startup context, and keeps writes disabled until a review surface exists.
It also includes `knowledge_capability` so hosts can classify AKBP as a
portable, cited, review-gated knowledge substrate instead of a chat dump,
runtime scratchpad, uncited vector cache, or bridge-owned memory format.

The default profile is read-only:

```bash
python3 cli/akbp.py --path ./my-kb client-config --name my-adapter
```

Use reviewed writes only when the adapter has review UI or a trusted local approval policy:

```bash
python3 cli/akbp.py --path ./my-kb client-config --name my-adapter --profile reviewed-writes
```

The generated config includes the server command, knowledge-base path, knowledge capability descriptor, startup `akbp.capabilities` request, required workflow profile, `akbp.doctor` health check, bounded session-start method, structured response contract, quality gates, tool-protocol bridge allowlists, and safety rules. Adapters should disable unavailable flows when `result.negotiation.satisfied` is false, follow `doctor.adapter_readiness.recommended_profile` when the knowledge base is not ready for reviewed writes, show `doctor.next_steps` when `ready_for_adapter` is false, and branch on `ok` plus `error.code` instead of prose.

Use `first_run_sequence.steps` as the adapter install checklist. Stop at the
first failed required step, show its structured failure, and keep the
integration read-only until the failing setup or review-surface requirement is
fixed.

The `quality_gates` section tells adapters when startup context is safe to use in a plan: request bounded cited context with `max_chars`, require at least one recalled item, require citations, surface warnings and budget truncation, and continue without recalled memory when context is empty or uncited. Reviewed-write configs also list the preview fields an adapter must show before retrying with `approved:true`.

The `maintenance` section gives adapters a small recurring health loop: verify cited source ids before trusting old claims, re-run `doctor` before enabling stricter profiles, check export bundles before sharing or importing them, and refresh the index after approved writes. Treat source drift, missing evidence, empty startup context, and unsupported profiles as blockers to surface, not prose to bury.

The `tool_protocol_bridge` section is for tool-protocol hosts. It exposes a read-only allowlist for `akbp.session.start`, `akbp.context`, `akbp.search`, `akbp.cite`, source verification, and import checks; lists blocked write methods by default; includes `host_tool_manifest` for hosts that need concrete tool names, descriptions, safety metadata, schema refs, stdio command, and preserved response fields; and documents the reviewed-write wrapper pattern where previews require `dry_run:true` and apply requires `approved:true` for the exact reviewed method, path, and params. See `docs/TOOL_PROTOCOL_BRIDGE.md` before publishing a bridge.

For scripts or adapter installers, run a profile-specific preflight before wiring a host:

```bash
python3 cli/akbp.py --path ./my-kb doctor --profile read-only
```

`doctor --profile` returns the same JSON health report and exits non-zero when the requested workflow profile is not ready, even if the knowledge base has no hard setup errors. Use this to avoid enabling a read-only, startup-context, or reviewed-write adapter against a KB that still needs indexing, evidence, or review readiness work.

The doctor report also includes `security_posture` so adapters can machine-check the write boundary before enabling memory. The reference posture requires dry-run previews followed by `approved:true` apply requests, reports which paths redact secret-like values, and lists safe review methods such as `akbp.import_check`, `akbp.export_check`, and `akbp.source.verify`.

## Conformance

`akbp conformance --level 0` checks the minimal file convention: `AKBP.md`, `akbp.json`, portable artifact paths, and required card capabilities.

`akbp conformance --level 1` also validates structured claims: required fields, unique IDs, lifecycle status, confidence range, and evidence shape.

`akbp conformance --level 2` validates the retrieval contract by exercising query results and protocol-shaped context items.

`akbp conformance --level 3` validates lifecycle relations such as contradictions, supersession, and support edges.

## Sources

`akbp source add` records immutable source material before claims cite it. For local files, the CLI records a SHA-256 hash when the file exists.

`akbp source verify --fail-on-issue` re-checks recorded file sources against their stored hashes and separates verified, changed, missing, and unchecked evidence.

## Export

`akbp export` emits a portable JSON bundle containing the card, claims, sources, entities, relations, and a self-describing manifest. The manifest records artifact paths, SHA-256 hashes when files exist, object counts, safety flags, and verification metadata. It is intentionally separate from local indexes or engine-owned state.

`akbp export-check bundle.json --fail-on-issues` validates a bundle before another agent trusts it. It checks JSON shape, manifest presence, object counts, artifact hash format, safety flags, and secret-like values.

## Contradictions

`akbp contradict` records a typed relation between two claims and marks both active claims as `contested`. This keeps conflict information explicit instead of silently overwriting old knowledge.

## SQLite index

`akbp index` builds `.akbp/state.db` using SQLite FTS5 over claims and wiki pages. `akbp index --incremental` only rewrites changed documents and removes stale entries. After an index exists, write commands refresh it incrementally so newly remembered, ingested, superseded, contradicted, or crystallized knowledge is searchable without a manual reindex. `akbp search` sanitizes user input into a safe FTS query, preserves explicit `AND`, `OR`, and `NOT` operators when they are used safely, defaults plain terms to `OR`, uses the local index when present, and falls back to portable JSONL/markdown query otherwise.

## Search query syntax

`akbp search` uses the local SQLite FTS5 index when `.akbp/state.db` exists, otherwise it falls back to JSONL/Markdown scanning.

Supported query forms:

- `rollback` searches one term.
- `rollback release` searches either term by default.
- `rollback AND release` requires both terms.
- `rollback OR release` accepts either term explicitly.
- `rollback NOT deprecated` excludes a term.
- `"release checklist"` searches a phrase.
- `deploy*` searches a token prefix.
- `akbp.session.start` searches a dotted method name as a phrase, not as three broad OR terms.

The CLI returns the generated `fts_query` with every indexed search response so agents can inspect how user text was normalized before trusting results. Queries with no safe searchable terms, including a leading standalone `NOT` or operator-only text, return an empty `fts_query` and empty result set instead of falling back to broad text scanning. Dangling trailing operators are removed before execution, so `JSONL AND` searches the safe `JSONL` term instead of passing malformed FTS syntax through to SQLite.
