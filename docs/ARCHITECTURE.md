# AKBP Architecture

AKBP is a local-first protocol and reference implementation for durable agent knowledge. The architecture is intentionally small: portable files are the source of truth, while local indexes and tool-server envelopes make the knowledge base practical for agents.

## System boundary

```text
Agent runtime / IDE / task runner
        │
        │ CLI commands or JSONL tool requests
        ▼
Reference interface layer
  - akbp console script
  - akbp-tool-server JSONL server
        │
        ▼
Protocol operations
  - initialize and validate a knowledge base
  - register and verify sources
  - ingest reviewed source material
  - remember cited claims
  - crystallize session transcripts
  - retrieve search results and context packs
  - export, check, import, and audit bundles
        │
        ▼
AKBP knowledge base
  - AKBP.md
  - akbp.json
  - wiki/*.md
  - claims/claims.jsonl
  - graph/entities.jsonl
  - graph/relations.jsonl
  - raw/sources/*
  - .akbp/audit.log.jsonl
        │
        ▼
Local runtime state
  - .akbp/state.db SQLite FTS5 index
```

## Source of truth

Portable AKBP artifacts are the source of truth:

- `AKBP.md`: human entry point for agents and maintainers.
- `akbp.json`: machine-readable Knowledge Base Card.
- `wiki/`: compiled markdown knowledge.
- `claims/claims.jsonl`: atomic claims with evidence, confidence, status, and lifecycle fields.
- `graph/entities.jsonl`: entities referenced by claims and pages.
- `graph/relations.jsonl`: typed relations and lifecycle links.
- `raw/sources/`: optional copied source material.
- `.akbp/audit.log.jsonl`: append-only operation history.

The SQLite database is rebuildable local state. It must not become the only copy of durable knowledge.

## Reference implementation layers

### CLI layer

The CLI is the direct developer interface. It supports local workflows such as:

```bash
akbp init
akbp source add notes.md --type file
akbp ingest notes.md --dry-run
akbp remember "Decision text" --evidence source_id
akbp crystallize transcript.md --dry-run
akbp index --incremental
akbp search "release checklist"
akbp context "continue this task"
akbp export --output bundle.json
akbp export-check bundle.json --fail-on-issues
akbp import-check bundle.jsonl --fail-on-rejected
akbp conformance --level 3
```

### JSONL tool-server layer

The JSONL server is for agent runtimes. Each request is one JSON object and each response is one JSON object.

Core read methods:

```text
akbp.capabilities
akbp.status
akbp.search
akbp.context
akbp.cite
akbp.audit
akbp.export
akbp.export_check
akbp.source.verify
akbp.conformance
```

Core write-capable methods:

```text
akbp.remember
akbp.source.add
akbp.ingest
akbp.import_apply
akbp.supersede
akbp.contradict
akbp.crystallize_session
```

Write-capable methods use review boundaries:

1. Preview with request-level `dry_run:true` when supported.
2. Surface `review_required`, rejected objects, warnings, and `apply_instruction`.
3. Apply only with request-level `approved:true` or an explicit trusted local policy.
4. Record audit metadata for durable writes.

### Storage layer

The storage layer writes portable artifacts first and rebuildable indexes second.

Rules:

- Claims and graph records are append-friendly JSONL.
- Source evidence is identified with source ids and hashes where possible.
- Search indexes can be deleted and rebuilt from portable artifacts.
- Export bundles include manifests and hashes.
- Import checks reject unknown source evidence and secret-like values before apply.

### Retrieval layer

The current reference retrieval layer uses SQLite FTS5 for local exact/prefix search and context-pack assembly.

Query handling intentionally accepts a small safe subset:

- plain tokens
- quoted phrases
- `AND`, `OR`, `NOT`
- trailing `*` prefix matching on simple word tokens

Punctuation-only tokens are ignored before reaching SQLite FTS5.

### Conformance layer

Conformance levels describe what a knowledge base supports:

- Level 0: file convention.
- Level 1: structured claims and evidence.
- Level 2: retrieval and context packs.
- Level 3: lifecycle relations.

The reference implementation validates these levels through CLI smoke tests, benchmark fixtures, and `akbp conformance`.

## Adapter contract

Adapters translate runtime behavior into AKBP calls. They must not create a separate durable memory format.

Adapter responsibilities:

- call `akbp.capabilities` before assuming methods or schemas
- retrieve cited startup context with `akbp.context` or `akbp.search`
- preview writes before apply
- preserve source ids and evidence hashes
- branch on structured `error.code`
- exclude secrets, tokens, cookies, auth headers, private DMs, and private logs by default
- keep durable output in AKBP artifacts

See `docs/ADAPTER_AUTHOR_QUICKSTART.md` and `docs/ADAPTER_REVIEW_CHECKLIST.md`.
For a developer-facing map of how AKBP fits under tool/context protocols,
agent-to-agent handoffs, and agent UI surfaces, see
`docs/DEVELOPER_PROTOCOL_FIT.md`.

## Build and validation architecture

The public validation gate is `make validate`:

```text
make guard
make test
make smoke
make benchmark-score
make benchmark
make install-smoke
```

CI runs that gate on Python 3.9, 3.10, 3.11, and 3.12. CI also builds source and wheel distributions.

## Non-goals for the reference implementation

The reference implementation does not require:

- a hosted backend
- a proprietary database
- a web UI
- runtime-specific private storage
- network access for core local flows

Those can exist around AKBP, but the protocol must remain inspectable, portable, and usable from a local repository.
