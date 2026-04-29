# AKBP

Agent Knowledge Base Protocol.

Agents should not start every session with amnesia.

AKBP is an open, local-first protocol for agent-maintained knowledge bases. It lets AI agents compile, update, cite, supersede, and share knowledge across sessions, tools, and runtimes.

The repo now includes a tiny reference CLI that can initialize a knowledge base, remember claims, crystallize transcripts, query memory, and return agent-ready context packs.

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
    tool protocol_CONTRACT.md
    ADAPTERS.md
    BENCHMARK.md
    SCHEMAS.md
    TOOL_CONTRACT.md
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
    coding-agent/
    research/
    personal/
  adapters/
    claude-code/
    codex/
    cursor/
    openclaw/
    gemini-cli/
  cli/
  tool-server/
  benchmark/
```

## Relationship to other protocols

AKBP is not trying to replace repository instruction files, tool protocol, or agent communication.

- Repository instruction files tell coding agents how to work inside a repo.
- Tool protocols let agents call tools and retrieve context.
- Agent communication protocols let agents communicate and collaborate.
- AKBP defines durable, portable knowledge that agents can discover, update, cite, and sync.

## Status

Draft protocol with a small reference CLI. The next milestone is protocol-standard readiness: adoption convention, Knowledge Base Card, versioned spec, governance, and conformance tests.
