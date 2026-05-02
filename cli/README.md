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
python3 cli/akbp.py init --path ./my-kb
python3 cli/akbp.py --path ./my-kb remember "This project uses Bun instead of npm" --type decision --evidence README.md
python3 cli/akbp.py --path ./my-kb query "Bun npm"
python3 cli/akbp.py --path ./my-kb index
python3 cli/akbp.py --path ./my-kb index --incremental
python3 cli/akbp.py --path ./my-kb search "Bun npm"
python3 cli/akbp.py --path ./my-kb context "continue the package manager migration"
python3 cli/akbp.py --path ./my-kb cite claim_123
python3 cli/akbp.py --path ./my-kb supersede claim_123 "Use the stdlib CLI until package metadata exists" --type decision --evidence cli/akbp.py
python3 cli/akbp.py --path ./my-kb contradict claim_123 claim_456 --evidence source_123
python3 cli/akbp.py --path ./my-kb conformance --level 3
python3 cli/akbp.py --path ./my-kb ingest notes.md --claim "The project ships small verified batches." --claim-type decision
python3 cli/akbp.py --path ./my-kb crystallize transcript.md
python3 cli/akbp.py --path ./my-kb crystallize transcript.md --apply
python3 cli/akbp.py --path ./my-kb lint
```

This implementation writes portable markdown and JSONL artifacts. It is intentionally small so other implementations can copy the behavior.

## Ingest

`akbp ingest notes.md` imports a local file into `wiki/imports/`, records a source in `raw/sources/sources.jsonl`, extracts lightweight signals from headings and decision-like lines, and redacts common token/key patterns from the imported page. Use `--claim` to create one evidence-backed claim while importing; claim text is redacted with the same safety filter before durable write.

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

## Conformance

`akbp conformance --level 0` checks the minimal file convention: `AKBP.md`, `akbp.json`, portable artifact paths, and required card capabilities.

`akbp conformance --level 1` also validates structured claims: required fields, unique IDs, lifecycle status, confidence range, and evidence shape.

`akbp conformance --level 2` validates the retrieval contract by exercising query results and protocol-shaped context items.

`akbp conformance --level 3` validates lifecycle relations such as contradictions, supersession, and support edges.

## Sources

`akbp source add` records immutable source material before claims cite it. For local files, the CLI records a SHA-256 hash when the file exists.

## Export

`akbp export` emits a portable JSON bundle containing the card, claims, sources, entities, and relations. It is intentionally separate from local indexes or engine-owned state.

## Contradictions

`akbp contradict` records a typed relation between two claims and marks both active claims as `contested`. This keeps conflict information explicit instead of silently overwriting old knowledge.

## SQLite index

`akbp index` builds `.akbp/state.db` using SQLite FTS5 over claims and wiki pages. `akbp index --incremental` only rewrites changed documents and removes stale entries. After an index exists, write commands refresh it incrementally so newly remembered, ingested, superseded, contradicted, or crystallized knowledge is searchable without a manual reindex. `akbp search` sanitizes user input into a safe FTS query, uses the local index when present, and falls back to portable JSONL/markdown query otherwise.
