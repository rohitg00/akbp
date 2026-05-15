# Developer Protocol Fit

AKBP is the durable knowledge layer underneath agent runtimes, tool bridges, agent-to-agent handoffs, and agent UI surfaces. It does not compete with those protocols. It gives them a portable place to store reviewed project knowledge after a session, task, or handoff proves something worth keeping.

## Developer view

```text
Developer
  |
  | asks an agent to continue work
  v
Agent runtime, IDE agent, local assistant, or hosted worker
  |
  | calls a host protocol for tools, handoffs, or UI
  v
Bridge or adapter
  |
  | forwards bounded JSONL requests
  v
AKBP tool server or CLI
  |
  | reads and writes reviewed artifacts
  v
AKBP knowledge base
  - AKBP.md
  - akbp.json
  - wiki/*.md
  - claims/claims.jsonl
  - graph/*.jsonl
  - raw/sources/*
  - .akbp/audit.log.jsonl
```

The runtime can change. The host protocol can change. The project knowledge should remain inspectable files with citations, lifecycle state, source hashes, and audit history.

## Where AKBP sits

| Adjacent layer | What that layer is good at | AKBP responsibility |
| --- | --- | --- |
| Tool and context protocol | Exposes tools, resources, prompts, and local capabilities to agents | Provide cited context and review-gated memory operations behind the bridge |
| Agent-to-agent protocol | Moves tasks, messages, state, and responsibility between agents | Give both agents the same reviewed project memory instead of copied chat summaries |
| Agent UI protocol | Streams agent state, actions, controls, and approvals into a user interface | Supply review metadata, warnings, citations, and apply instructions the UI can render |
| Runtime instruction files | Tell one agent how to behave in one repo or environment | Store durable project facts and decisions that should survive runtime switches |
| Retrieval or vector store | Finds relevant text or embeddings | Keep the source-of-truth artifacts, lifecycle semantics, and exportable context packs |

## Read path

Use AKBP at the start of substantial work:

```text
runtime starts
  -> adapter discovers AKBP capabilities
  -> adapter checks knowledge-base health
  -> runtime requests task-scoped context
  -> AKBP returns bounded context with citations and source ids
  -> runtime plans with evidence instead of re-deriving history
```

Minimal JSONL shape:

```json
{"id":"caps","method":"akbp.capabilities"}
{"id":"status","method":"akbp.status","path":"."}
{"id":"start","method":"akbp.session.start","path":".","params":{"task":"continue release work","limit":5}}
```

The adapter should preserve `ok`, `result`, `error.code`, citations, source ids, and budget fields when translating into a host protocol response.

## Write path

Use AKBP only for durable knowledge: decisions, constraints, benchmark results, validated architecture facts, incident learnings, and lifecycle changes.

```text
agent finds durable knowledge
  -> adapter previews the memory write with dry_run:true
  -> AKBP returns review_required, warnings, skipped records, and apply_instruction
  -> UI or local policy gets explicit approval
  -> adapter repeats the same request with approved:true
  -> AKBP writes portable artifacts and audit events
  -> adapter refreshes the local index
```

Minimal JSONL shape:

```json
{"id":"preview","method":"akbp.remember","path":".","dry_run":true,"params":{"text":"Decision: release notes must cite validation output."}}
{"id":"apply","method":"akbp.remember","path":".","approved":true,"params":{"text":"Decision: release notes must cite validation output."}}
{"id":"index","method":"akbp.index","path":".","approved":true,"params":{"incremental":true}}
```

The apply request must repeat the reviewed method, path, and params. A bridge must not silently rewrite claim text, evidence, entities, locators, or transcript paths between preview and apply.

## Handoff path

When work moves between agents, AKBP is the shared project record:

```text
Agent A completes work
  -> previews durable summary or decision
  -> approved write lands in AKBP artifacts
  -> search index refreshes

Agent B starts later
  -> retrieves task-scoped context from AKBP
  -> sees the same cited decision and lifecycle state
  -> supersedes or contradicts stale knowledge explicitly when needed
```

This is the practical difference between a protocol-level knowledge base and a runtime memory cache: the next agent does not need the previous chat transcript to understand the reviewed project state.

## Adapter rules

- Start read-only until the host has a visible review surface.
- Call capabilities before assuming methods, schemas, or profiles.
- Treat `approval_required` as a stop signal.
- Keep private logs, credentials, cookies, tokens, raw chats, and scratch reasoning out of durable memory by default.
- Store durable state in AKBP artifacts, not in bridge-owned files.
- Keep `.akbp/` rebuildable runtime state local.
- Export only portable markdown and JSONL artifacts plus manifests and hashes.

## Architecture test

A developer-facing integration is credible when it can prove:

1. A new runtime gets cited startup context in one call.
2. A direct write without approval fails with a structured error.
3. A dry-run write returns review metadata without changing artifacts.
4. An approved write creates portable records and audit events.
5. A different runtime can retrieve the approved knowledge later.
6. Export and import checks pass without bridge-owned state.

Run the repo gate before shipping adapter changes:

```bash
make guard
make test
make smoke
make install-smoke
```

