# AKBP Architecture

## System goal

AKBP makes one durable knowledge base usable by many agents.

The first target is coding-agent memory, because that is where the pain is sharpest: every Claude Code, Cursor, Codex, OpenClaw, Gemini CLI, or custom agent session starts by rediscovering project context.

## High-level architecture

```text
             ┌──────────────────────────┐
             │        AI Agents          │
             │ Claude, Cursor, Codex,    │
             │ OpenClaw, Gemini, tool protocol     │
             └────────────┬─────────────┘
                          │
                          │ CLI / tool protocol / SDK / HTTP
                          ▼
┌─────────────────────────────────────────────────────┐
│                    AKBP Engine                       │
│                                                     │
│  ┌───────────┐  ┌───────────┐  ┌────────────────┐  │
│  │ Ingestion │  │ Retrieval │  │ Crystallizer   │  │
│  └───────────┘  └───────────┘  └────────────────┘  │
│  ┌───────────┐  ┌───────────┐  ┌────────────────┐  │
│  │ Lifecycle │  │ Lint      │  │ Sync/Audit     │  │
│  └───────────┘  └───────────┘  └────────────────┘  │
└───────────────────────┬─────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│                  AKBP Knowledge Base                 │
│                                                     │
│ raw/      immutable source material                  │
│ wiki/     markdown pages for humans                  │
│ claims/   atomic claims with lifecycle metadata      │
│ graph/    entities and typed relations               │
│ indexes/  BM25, vectors, graph snapshots             │
│ logs/     append-only audit and operation history    │
└─────────────────────────────────────────────────────┘
```

## Storage model

AKBP should use a hybrid storage model:

1. Markdown for human-readable compiled knowledge.
2. JSONL for portable claims/entities/relations/evidence.
3. SQLite for local indexing, query speed, and transaction safety.
4. Optional vector index for semantic search.
5. Git for version history, rollback, branching, review, and team workflows.

This avoids the common trap of making the database the only source of truth. The durable protocol artifacts remain inspectable.

## Core modules

### 1. Ingestion

Input:

```text
file
folder
URL
PDF
image/screenshot
meeting transcript
agent session transcript
code diff
issue thread
```

Output:

```text
source record
candidate claims
candidate entities
candidate relations
page updates
index updates
audit entry
```

Ingestion should classify before extraction. A book, a code session, a Slack thread, and a GitHub issue should not use the same extraction prompt.

### 2. Crystallizer

The crystallizer converts work into durable knowledge.

For a coding-agent session it extracts:

```text
task summary
files touched
decisions made
bugs discovered
commands that mattered
open questions
user preferences
project facts
workflow changes
```

It then writes claims, updates pages, and links entities.

### 3. Retrieval

Retrieval should be composable:

```text
BM25: exact terms, file names, APIs, repos
Vector: semantic similarity and vague questions
Graph: dependencies, ownership, causal chains, supersession
RRF: result fusion
Evidence reranking: prefer cited, fresh, high-confidence claims
```

The agent should not receive raw search dumps. It should receive a compact context pack:

```text
relevant facts
current decisions
warnings/contradictions
source citations
freshness notes
suggested pages to read
```

### 4. Lifecycle manager

The lifecycle manager prevents memory rot.

Responsibilities:

```text
confidence updates
freshness decay
supersession
contradiction handling
promotion from working to stable
archival of low-value claims
source invalidation
```

### 5. Linter

The linter keeps the knowledge base healthy.

Checks:

```text
orphan pages
missing evidence
broken wikilinks
duplicate entities
stale claims
contradictions
claims without page references
pages without index entries
secrets or sensitive values
large pages that need splitting
```

### 6. Sync and audit

AKBP must support multiple agents writing to one knowledge base.

Minimum sync rules:

```text
append-only audit log
stable object IDs
optimistic concurrency
last-write-wins only for non-conflicting metadata
manual review for claim/content conflicts
all destructive operations reversible
```

## Interfaces

### CLI

```bash
akbp init
akbp ingest <file|url|folder>
akbp query "what do we know about X?"
akbp context "continue this task"
akbp remember "fact or observation"
akbp crystallize <transcript.md>
akbp index --incremental
akbp search "what changed?"
akbp lint
akbp export
```

### tool protocol

```text
akbp.capabilities
akbp.status
akbp.query
akbp.context
akbp.index
akbp.search
akbp.remember
akbp.conformance
akbp.export
akbp.audit
akbp.cite
akbp.source.add
akbp.ingest
akbp.supersede
akbp.contradict
akbp.crystallize_session
```

### Adapter contract

Each agent adapter defines:

```text
where instructions live
how to call AKBP
how session-start context is retrieved
how session-end crystallization runs
what data is private by default
how secrets are filtered
how conflicts are surfaced
```

## MVP architecture decision

For v0.1, build the reference engine as:

```text
TypeScript or Python CLI
SQLite local DB
Markdown + JSONL protocol artifacts
tool-server implementation wrapper
No hosted backend
No UI
```

Reason: protocol adoption matters more than UI polish. Let Obsidian, GitHub, editors, and existing agent UIs be the interface.

## Local search index

The reference CLI can build `.akbp/state.db` with SQLite FTS5. This is engine-owned state, not a portable protocol artifact. Portable knowledge remains in markdown, JSONL claims, sources, entities, and relations.
