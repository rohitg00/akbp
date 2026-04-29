---
title: "AKBP Build Plan"
type: "build-plan"
status: "draft"
tags:
  - "akbp"
  - "build-plan"
created: "2026-04-29"
---

# AKBP Build Plan

## Goal

Ship AKBP v0.1 as a spec-first repo with a minimal reference implementation.

The product should prove one loop:

```text
agent session ends
→ transcript is crystallized
→ claims/pages/entities are updated
→ next agent session retrieves useful context
```

## Phase 0: Repo foundation

Deliverables:

```text
README.md
SPEC.md
docs/ARCHITECTURE.md
docs/BUILD_PLAN.md
docs/MCP_CONTRACT.md
docs/ADAPTERS.md
docs/BENCHMARK.md
schemas/*.schema.json
examples/*
```

Definition of done:

- A developer can understand the protocol in 10 minutes.
- A tool builder can implement Level 0 or Level 1 from the spec.
- The repo makes clear that AKBP is a protocol, not another notes app.

## Phase 1: Portable object schemas

Create JSON schemas for:

```text
claim
entity
relation
evidence
source
page
audit event
context pack
```

Current draft schemas live in `schemas/` and are described in `docs/SCHEMAS.md`.

Definition of done:

- Schemas validate sample objects.
- Every schema has required fields, optional fields, examples, and lifecycle metadata.

## Phase 2: Minimal CLI

Commands:

```bash
akbp init
akbp remember "..."
akbp query "..."
akbp crystallize transcript.md
akbp lint
akbp status
```

Implementation scope:

- local workspace only
- markdown + JSONL writes
- SQLite index optional but recommended
- no vector search initially
- no hosted service

Definition of done:

- Run `akbp init` and get a valid Level 0 knowledge base.
- Run `akbp remember` and produce a claim with evidence/status.
- Run `akbp crystallize` on a transcript and update wiki pages plus claims.
- Run `akbp query` and return a context pack.

## Phase 3: MCP server

Expose the CLI functionality through MCP tools.

Minimum tools:

```text
akbp.search
akbp.get_context
akbp.remember
akbp.crystallize_session
akbp.lint
akbp.cite
```

Definition of done:

- Claude Desktop or any MCP client can call AKBP tools.
- Tool outputs are compact and citation-friendly.
- Writes are audited.

## Phase 4: Agent adapters

Adapters for:

```text
Claude Code
Codex
Cursor
OpenClaw
Gemini CLI
```

Each adapter should include:

```text
install instructions
agent instruction template
session start pattern
session end pattern
privacy defaults
example config
```

Definition of done:

- A user can connect at least two different agents to the same AKBP folder.
- The second agent can retrieve useful context written by the first agent.

## Phase 5: Retrieval upgrade

Add:

```text
BM25 search
vector search optional
entity graph traversal
RRF fusion
context pack generation
```

Definition of done:

- Query can retrieve exact terms and semantic matches.
- Graph traversal can answer downstream/related questions.
- Context pack includes citations and freshness.

## Phase 6: Benchmark

Benchmark tasks:

1. Cross-session preference recall.
2. Decision recall with citations.
3. Contradiction detection.
4. Supersession of stale facts.
5. Non-keyword retrieval through graph traversal.
6. Secret redaction on ingest.
7. Multi-agent write conflict handling.
8. Source-change invalidation.
9. Large-document chunking.
10. Human-readable markdown quality.

Definition of done:

- Benchmark can run locally.
- Results are reproducible.
- New engines/adapters can compare compliance.

## What not to build first

Do not start with:

```text
hosted SaaS
visual UI
complex collaboration dashboard
enterprise permissions
fully automatic browser capture
model-specific deep integrations
```

Those can come later. The first win is interoperability.

## Recommended first public issue list

1. Define claim schema.
2. Define evidence schema.
3. Define entity/relation schema.
4. Define context pack output format.
5. Build `akbp init`.
6. Build `akbp remember`.
7. Build `akbp crystallize`.
8. Build MCP tool contract.
9. Add Claude Code adapter.
10. Add Codex/OpenClaw adapter.
