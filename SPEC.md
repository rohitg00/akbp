---
title: "AKBP Specification v0.1 Draft"
type: "spec"
status: "draft"
tags:
  - "akbp"
  - "specification"
  - "protocol"
created: "2026-04-29"
---

# AKBP Specification v0.1 Draft

## 1. Definition

AKBP, Agent Knowledge Base Protocol, is a protocol for creating, updating, retrieving, and sharing durable knowledge across AI agents.

It is not a notes app, RAG product, or model memory feature. It is the interoperability layer between agents and knowledge bases.

## 2. Core thesis

```text
RAG retrieves and forgets.
LLM Wiki compiles and compounds.
AKBP makes compiled knowledge portable across agents.
```

## 3. Design principles

1. Local-first: markdown and git must be usable without a hosted service.
2. Agent-neutral: the same knowledge base should work across Claude Code, Cursor, Codex, OpenClaw, Gemini CLI, MCP clients, and custom agents.
3. Evidence-backed: durable claims must cite evidence.
4. Lifecycle-aware: knowledge can be reinforced, contradicted, superseded, decayed, or archived.
5. Human-readable: humans should be able to browse the knowledge base in Obsidian, GitHub, editors, or terminals.
6. Machine-operable: agents need structured schemas, stable IDs, and retrieval APIs.
7. Safe by default: secrets and private data need visibility, redaction, and audit rules.
8. Progressive: a simple markdown wiki can be AKBP Level 0. A full graph/vector/MCP system can be Level 5.

## 4. Canonical folder contract

```text
.akbp/
  config.json
  state.db
  audit.log.jsonl
raw/
  sources/
wiki/
  index.md
  log.md
  entities/
  concepts/
  decisions/
  workflows/
  sessions/
claims/
  claims.jsonl
graph/
  entities.jsonl
  relations.jsonl
indexes/
  bm25/
  vectors/
  graph-snapshot.json
adapters/
  claude-code/
  codex/
  cursor/
  openclaw/
  gemini-cli/
```

Only `.akbp/` is engine-owned internal state. `raw/`, `wiki/`, `claims/`, and `graph/` are portable protocol artifacts.

## 5. Core objects

### Source

Immutable input material.

Examples: article, PDF, transcript, chat session, meeting note, screenshot, code diff, issue thread, Slack export, email export, voice transcript, web clip.

### Page

Human-readable compiled markdown.

A page is not a raw summary. It is the maintained synthesis for an entity, concept, decision, workflow, or session.

### Claim

Atomic durable assertion.

A claim is the smallest thing that can be cited, contradicted, superseded, reinforced, decayed, or archived.

### Entity

Typed object in the knowledge base.

Suggested entity types:

```text
person
project
repo
company
concept
decision
workflow
file
api
incident
source
agent
tool
team
system
```

### Relation

Typed edge between entities or claims.

Suggested relation types:

```text
uses
depends_on
contradicts
supersedes
supports
caused_by
owned_by
derived_from
similar_to
blocks
implements
references
```

### Evidence

Pointer to source material supporting a claim.

Evidence can point to a URL, file path, commit, transcript span, message ID, screenshot, PDF page, timestamp, or raw source hash.

## 6. Memory lifecycle

Every claim has a lifecycle status:

```text
working      newly observed, not yet consolidated
actionable   useful for current work
stable       repeatedly supported
contested    contradicted by other evidence
superseded   replaced by newer claim
archived     kept for history but not retrieved by default
redacted     hidden because of privacy or secret policy
```

## 7. Required agent operations

```text
remember        write a new observation or claim
retrieve        find relevant knowledge for a task
update          update an existing page or claim
contradict      mark a conflict between claims
supersede       replace stale knowledge with newer knowledge
forget          decay or archive low-value knowledge
cite            return evidence for an answer
crystallize     convert session output into durable knowledge
lint            check health, links, contradictions, orphans, staleness
sync            merge changes from multiple agents or users
```

## 8. Retrieval contract

AKBP engines must declare supported retrieval modes.

Level 0 requires index/log reading. Higher levels can add:

```text
bm25
vector
graph
hybrid_rrf
```

Recommended full retrieval:

```text
BM25 exact search
+ vector semantic search
+ graph traversal
+ reciprocal rank fusion
+ evidence reranking
```

## 9. Agent hooks

```text
on_session_start     retrieve relevant context
on_tool_result       optionally store important evidence
on_decision          write/update decision claims
on_source_added      ingest and compile new source
on_session_end       crystallize transcript into durable memory
on_schedule          lint, prune, decay, consolidate
on_conflict          surface contradiction or ask human
```

## 10. Page creation vs update rule

Create a page when the subject is durable, reusable, and likely to be independently referenced.

Update a page when new information strengthens, weakens, clarifies, contradicts, or supersedes an existing page.

When uncertain, create a claim first. Let lint/consolidation promote it into a page later.

## 11. Compliance levels

### Level 0: Markdown Wiki

Raw sources, wiki pages, `index.md`, `log.md`, and agent instructions.

### Level 1: Claims and Evidence

Atomic claims with evidence pointers and lifecycle status.

### Level 2: Search

BM25 or vector retrieval over pages, claims, and sources.

### Level 3: Graph

Typed entities and relationships with graph traversal.

### Level 4: Automation

Session hooks, ingest hooks, crystallization, lint, pruning, and MCP tools.

### Level 5: Collaboration

Shared/private scopes, multi-agent sync, conflict resolution, audit trail, and team access.
