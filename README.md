# AKBP

[![CI](https://github.com/rohitg00/akbp/actions/workflows/ci.yml/badge.svg)](https://github.com/rohitg00/akbp/actions/workflows/ci.yml)

Agent Knowledge Base Protocol.

Agents should not start every session with amnesia.

AKBP is an open, local-first protocol for agent-maintained knowledge bases. It lets AI agents compile, update, cite, supersede, and share knowledge across sessions, tools, and runtimes.

The repo now includes a tiny reference CLI that can initialize a knowledge base, remember claims, crystallize transcripts, query memory, and return agent-ready context packs.

CI runs `make validate`, which covers the public-reference guard, tests, CLI smoke flow, retrieval benchmarks, and install smoke flow on pushes and pull requests.

## Why

RAG retrieves and forgets. LLM Wiki compiles and compounds. AKBP makes that compiled knowledge portable across agents.

The current ecosystem is fragmented: Obsidian vaults, Markdown memories, tool-server implementations, coding-agent session logs, graph memory systems, local search tools, and custom second-brain apps. AKBP defines the common layer between them.

## Who it is for

- Coding agents that need memory across sessions
- Research agents that compile sources into durable knowledge
- Teams that need shared agent-readable context
- Obsidian and Markdown users who want agent-maintained notes
- tool protocol tool builders who need a standard memory contract

## What AKBP standardizes

- Folder structure
- Markdown page conventions
- Claim schema
- Entity schema
- Relationship schema
- Evidence/provenance schema
- Memory lifecycle rules
- Retrieval contract
- Agent hooks
- tool interface names
- Sync and conflict behavior
- Privacy and audit rules
- Benchmarks for durable agent knowledge

## Five-minute adoption

A minimal AKBP knowledge base starts with two files:

```text
AKBP.md      human-readable entry point for agents and maintainers
akbp.json    machine-readable Knowledge Base Card
```

Then add portable artifacts as the knowledge base matures:

```text
wiki/
claims/claims.jsonl
graph/entities.jsonl
graph/relations.jsonl
raw/sources/
```

Create the starter layout with:

```bash
python3 cli/akbp.py init
```

Or install the local CLI:

```bash
python3 -m pip install .
akbp --path ./my-kb init
```

See `docs/INSTALL.md` for install, build, and smoke-test instructions. See `docs/RELEASE.md` and `docs/RELEASE_NOTES_DRAFT.md` for release readiness, validation, and announcement prep.

## Quickstart

Run the end-to-end local flow in under five commands:

```bash
python3 cli/akbp.py --path ./my-kb init
python3 cli/akbp.py --path ./my-kb ingest notes.md --claim "Capture the durable decision from this note." --claim-type decision
python3 cli/akbp.py --path ./my-kb index --incremental
python3 cli/akbp.py --path ./my-kb search "durable decision"
python3 cli/akbp.py --path ./my-kb context "continue this project"
```

For a complete runnable example, see `docs/AGENT_FLOW.md` and `examples/end-to-end-agent-flow/`.

## First implementation target

The narrow MVP is coding-agent memory:

```text
agent finishes work
→ transcript is crystallized
→ facts, decisions, workflows, and open questions are extracted
→ wiki pages and claims are updated
→ next agent session retrieves better context automatically
```

## Repository layout

```text
akbp/
  README.md
  SPEC.md
  ROADMAP.md
  docs/
    ARCHITECTURE.md
    BUILD_PLAN.md
    ADAPTERS.md
    BENCHMARK.md
    INSTALL.md
    RELEASE.md
    RELEASE_NOTES_DRAFT.md
    SCHEMAS.md
    TOOL_CONTRACT.md
    AGENT_FLOW.md
    STANDARDS_TRACK.md
    KNOWLEDGE_BASE_CARD.md
  spec/
  schemas/
    claim.schema.json
    entity.schema.json
    relation.schema.json
    evidence.schema.json
    source.schema.json
    page.schema.json
    audit-event.schema.json
    context-pack.schema.json
  examples/
    level-0/
    level-1/
    level-3/
    end-to-end-agent-flow/
    coding-agent/
    research/
    personal/
  adapters/
    coding-agent-template/
    example-coding-agent/
    terminal-coding-agent/
    editor-coding-agent/
    openclaw/
    codex/
    claude-code/
    cursor/
  cli/
  tool-server/
  benchmarks/
```

## Relationship to other protocols

AKBP is not trying to replace repository instruction files, tool protocol, or agent communication.

- Repository instruction files tell coding agents how to work inside a repo.
- Tool protocols let agents call tools and retrieve context.
- Agent communication protocols let agents communicate and collaborate.
- AKBP defines durable, portable knowledge that agents can discover, update, cite, and sync.

## Status

Draft protocol with a small installable reference CLI, conformance checks, ingest, local search, retrieval benchmarks, adapter templates, a complete runtime-neutral adapter example, and a JSONL local tool server. The next milestones are stronger extraction, richer runtime-specific adapters, and optional retrieval backends.

## Examples

- `examples/level-0/` shows the minimal file convention.
- `examples/level-1/` shows structured claims with evidence.
- `examples/level-3/` shows lifecycle relations with concrete JSONL records.
- `examples/end-to-end-agent-flow/` shows ingest, remember, index, search, context, and cite flow.
- `examples/tool-server-approval-flow/` shows dry-run, `approval_required`, and approved JSONL write flow.

Validate them with:

```bash
python3 cli/akbp.py --path examples/level-0 conformance --level 0
python3 cli/akbp.py --path examples/level-1 conformance --level 1
python3 cli/akbp.py --path examples/level-3 conformance --level 3
```

## Local tool server

The repo includes a dependency-free JSONL tool server for local agent integrations:

```bash
echo '{"id":"1","method":"akbp.status","path":"."}' | python3 tool-server/akbp_tool_server.py
```

Write-capable tool calls are review-gated. Start with request-level `dry_run:true`; apply only after approval with request-level `approved:true`. Non-approved writes return a structured `approval_required` error instead of mutating the knowledge base.

```bash
echo '{"id":"2","method":"akbp.remember","path":".","dry_run":true,"params":{"text":"Agents need rollback paths"}}' | python3 tool-server/akbp_tool_server.py
echo '{"id":"2-apply","method":"akbp.remember","path":".","approved":true,"params":{"text":"Agents need rollback paths"}}' | python3 tool-server/akbp_tool_server.py
```
