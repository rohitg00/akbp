# AKBP

[![CI](https://github.com/rohitg00/akbp/actions/workflows/ci.yml/badge.svg)](https://github.com/rohitg00/akbp/actions/workflows/ci.yml)

> Agents should not start every session with amnesia.

AKBP is the Agent Knowledge Base Protocol: an open, local-first way for AI agents to compile durable project knowledge, cite where it came from, update it safely, and carry it across tools.

The short version: AKBP turns messy agent work into a portable knowledge base that the next agent session can actually use.

Today this repo ships a working reference CLI, a JSONL tool server, schemas, adapters, conformance checks, benchmarks, import/export safety checks, and CI across Python 3.9, 3.10, 3.11, and 3.12.

It is still alpha. It is not a 1.0 compatibility promise yet. It is ready for serious demos, adapter work, protocol feedback, and early dogfooding.

## Why this exists

RAG retrieves and forgets. Repository instruction files help agents behave, but they do not become a shared memory system. Chat transcripts contain useful decisions, but they are usually trapped in one runtime. Every new agent session pays the same context tax again.

AKBP gives agents a durable layer:

```text
agent finishes work
  -> transcript and sources are reviewed
  -> durable claims and wiki pages are written
  -> evidence and source hashes are kept
  -> local search/indexes are refreshed
  -> the next session gets cited context instead of guesswork
```

The goal is not another private memory database. The goal is a protocol that a coding agent, research agent, IDE, CLI, or second-brain tool can all read and write.

## What ships today

| Area | Current support |
|------|-----------------|
| Local knowledge base | `AKBP.md`, `akbp.json`, markdown wiki pages, JSONL claims, graph records, sources, audit log |
| CLI | `akbp init`, `source add`, `ingest`, `remember`, `crystallize`, `index`, `search`, `context`, `export`, `import-check`, `import-apply`, `conformance` |
| Tool server | JSONL server with `akbp.capabilities`, structured responses, schema-backed params, and structured errors |
| Safety | `dry_run:true`, `approved:true`, `approval_required`, review-gated writes, secret-like value rejection, source verification |
| Portability | Export manifests with artifact paths, SHA-256 hashes, object counts, safety flags, and verification metadata |
| Retrieval | SQLite FTS5 local search, context packs, citations, benchmark fixtures |
| Adapters | Templates and public-safe examples for coding-agent runtimes |
| Validation | `make validate`, GitHub CI matrix, package build artifact, install smoke tests |

## See it work

Run the complete public-alpha demo:

```bash
git clone https://github.com/rohitg00/akbp.git
cd akbp
make demo
```

The demo creates a fresh knowledge base, registers a source, ingests one durable release decision, verifies evidence, builds search, retrieves context, exports a portable bundle, checks the bundle, and runs level 3 conformance.

Expected success markers:

```text
AKBP quickstart demo
Initialized AKBP knowledge base at ...
"verified": 1
"results": [
"items": [
"ok": true
AKBP quickstart demo passed
```

If you prefer the direct CLI path:

```bash
python3 cli/akbp.py --path ./my-kb init
python3 cli/akbp.py --path ./my-kb source add notes.md --type file --title "Project notes"
python3 cli/akbp.py --path ./my-kb ingest notes.md --claim "Capture the durable decision from this note." --claim-type decision
python3 cli/akbp.py --path ./my-kb source verify --fail-on-issue
python3 cli/akbp.py --path ./my-kb index --incremental
python3 cli/akbp.py --path ./my-kb search "durable decision"
python3 cli/akbp.py --path ./my-kb context "continue this project"
```

## Install

For repo-local development:

```bash
python3 cli/akbp.py --help
```

For installed console scripts:

```bash
python3 -m pip install .
akbp --path ./my-kb init
akbp-tool-server < requests.jsonl
```

Full install and verification notes are in `docs/INSTALL.md`.

## The sprint loop for agents

AKBP is designed around the way coding agents actually work:

| Moment | AKBP action |
|--------|-------------|
| Session starts | Call `akbp.context` and `akbp.search` for cited project memory |
| Agent reads files or notes | Register evidence with `akbp.source.add` |
| Agent proposes durable memory | Preview with `akbp.ingest` or `akbp.crystallize_session` and `dry_run:true` |
| User or trusted policy approves | Apply with `approved:true` |
| Work finishes | Refresh index and audit durable writes |
| Another agent starts later | Retrieve compact context packs with citations |

The core rule: agents can suggest memory, but durable writes must be review-gated.

See `docs/AGENT_FLOW.md` and `examples/tool-server-approval-flow/`.

## The knowledge base format

A minimal AKBP knowledge base starts with two files:

```text
AKBP.md      human-readable entry point for agents and maintainers
akbp.json    machine-readable Knowledge Base Card
```

As the knowledge base matures, it adds portable artifacts:

```text
wiki/                  compiled markdown knowledge
claims/claims.jsonl    atomic claims with evidence and lifecycle state
graph/entities.jsonl   entities referenced by claims and pages
graph/relations.jsonl  typed relations and lifecycle links
raw/sources/           optional copied source material
.akbp/audit.jsonl      append-only operation history
```

Local runtime state lives under `.akbp/`, including the rebuildable SQLite FTS5 index. Portable knowledge remains in markdown and JSONL.

## Tool server contract

Agents talk to AKBP through newline-delimited JSON.

Capability discovery:

```json
{"id":"caps-1","method":"akbp.capabilities"}
```

Context retrieval:

```json
{"id":"ctx-1","method":"akbp.context","path":".","params":{"query":"current release decisions","limit":5}}
```

Write preview:

```json
{"id":"write-preview-1","method":"akbp.remember","path":".","dry_run":true,"params":{"text":"Decision: keep public alpha releases small and evidence-backed."}}
```

Approved write:

```json
{"id":"write-apply-1","method":"akbp.remember","path":".","approved":true,"params":{"text":"Decision: keep public alpha releases small and evidence-backed."}}
```

Adapters should branch on `error.code`, not free-form strings. See `docs/TOOL_CONTRACT.md` and `examples/tool-error-handling/`.

## Adapter path

Start here if you want AKBP inside a coding agent, IDE agent, task runner, or local assistant runtime:

1. Read `docs/ADAPTER_AUTHOR_QUICKSTART.md`.
2. Copy `adapters/coding-agent-template/`.
3. Call `akbp.capabilities` at startup.
4. Retrieve context before planning.
5. Preview writes with `dry_run:true`.
6. Apply only with `approved:true` or an explicit trusted local policy.
7. Keep durable output in AKBP artifacts.
8. Run `make validate`.

Tracked adapter directories:

```text
adapters/coding-agent-template/
adapters/example-coding-agent/
adapters/terminal-coding-agent/
adapters/editor-coding-agent/
adapters/openclaw/
adapters/codex/
adapters/claude-code/
adapters/cursor/
adapters/gemini-cli/
```

## Architecture

```text
Agent runtime / IDE / task runner
        |
        | CLI commands or JSONL tool requests
        v
Reference interface layer
  - akbp console script
  - akbp-tool-server JSONL server
        |
        v
Protocol operations
  - initialize and validate
  - register and verify sources
  - ingest reviewed source material
  - remember cited claims
  - crystallize session transcripts
  - retrieve search results and context packs
  - export, check, import, and audit bundles
        |
        v
AKBP knowledge base
  - markdown and JSONL source-of-truth artifacts
  - append-only audit log
  - rebuildable local SQLite FTS5 index
```

Read the current architecture map in `docs/ARCHITECTURE.md`.

## Validation

The public gate is:

```bash
make validate
```

It runs:

```text
make guard
make test
make smoke
make benchmark-score
make benchmark
make install-smoke
```

GitHub CI runs full validation across Python 3.9, 3.10, 3.11, and 3.12, then builds package artifacts.

The repo currently includes:

- `tests/` for CLI, tool server, schemas, docs, adapters, and repo quality
- `benchmarks/fixtures/` for durable retrieval, citation, write-safety, import/apply, and capability scenarios
- `examples/quickstart-demo/` for the one-command happy path
- `docs/TROUBLESHOOTING.md` for common local failures

## Conformance levels

| Level | Meaning |
|-------|---------|
| 0 | File convention: `AKBP.md` and `akbp.json` |
| 1 | Structured claims and evidence |
| 2 | Retrieval and context packs |
| 3 | Lifecycle relations |

Check a knowledge base:

```bash
akbp --path ./my-kb conformance --level 3
```

## Security model

AKBP is local-first and review-gated. Write-capable JSONL tool methods require dry-run previews and explicit approval before durable writes. The reference implementation redacts common secret-like values in ingest, import/export checks, and generic dry-run previews. See [SECURITY.md](SECURITY.md) and [docs/SECURITY_MODEL.md](docs/SECURITY_MODEL.md).

## What AKBP is not

AKBP does not replace:

- repository instruction files
- tool protocol servers
- chat history
- vector databases
- Obsidian or markdown editors
- hosted memory products

AKBP is the durable knowledge contract below those tools.

## Roadmap to 1.0

Before 1.0, AKBP still needs:

- broader real-world adapter dogfooding
- stronger import/export compatibility fixtures
- clearer versioning and migration policy
- larger retrieval quality benchmarks
- more release and security review hardening

Alpha status is intentional. The project should earn stability through usage and tests, not marketing language.

## Repository layout

```text
akbp/
  README.md
  AKBP.md
  SPEC.md
  ROADMAP.md
  docs/
  spec/
  schemas/
  examples/
  adapters/
  cli/
  tool-server/
  benchmarks/
  tests/
```

## Start here

- New user: run `make demo`.
- Adapter author: read `docs/ADAPTER_AUTHOR_QUICKSTART.md`.
- Protocol reviewer: read `docs/ARCHITECTURE.md`, `docs/TOOL_CONTRACT.md`, and `schemas/`.
- Release reviewer: run `make validate`, then read `docs/RELEASE.md`.
- Troubleshooting: read `docs/TROUBLESHOOTING.md`.

## License

MIT
