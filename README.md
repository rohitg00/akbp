# AKBP

Agent Knowledge Base Protocol.

Agents should not start every session with amnesia.

AKBP is an open, local-first protocol for agent-maintained knowledge bases. It lets AI agents compile, update, cite, supersede, and share knowledge across sessions, tools, and runtimes.

The repo now includes a tiny reference CLI that can initialize a knowledge base, remember claims, crystallize transcripts, query memory, and return agent-ready context packs.

## Why

RAG retrieves and forgets. LLM Wiki compiles and compounds. AKBP makes that compiled knowledge portable across agents.

The current ecosystem is fragmented: Obsidian vaults, Markdown memories, MCP servers, coding-agent session logs, graph memory systems, local search tools, and custom second-brain apps. AKBP defines the common layer between them.

## Who it is for

- Coding agents that need memory across sessions
- Research agents that compile sources into durable knowledge
- Teams that need shared agent-readable context
- Obsidian and Markdown users who want agent-maintained notes
- MCP tool builders who need a standard memory contract

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
- MCP tool names
- Sync and conflict behavior
- Privacy and audit rules
- Benchmarks for durable agent knowledge

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
    MCP_CONTRACT.md
    ADAPTERS.md
    BENCHMARK.md
    SCHEMAS.md
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
  mcp/
  benchmark/
```

## Status

Spec-first. CLI and MCP reference implementation next.
