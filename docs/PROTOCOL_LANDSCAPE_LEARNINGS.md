# Protocol landscape learnings

This note tracks public signals from adjacent agent-memory and agent-harness projects and turns them into AKBP usability work.

It is not a vendor ranking. It is a product checklist for making AKBP easier for real users to understand, run, and adopt.

## Last scan

- Date: 2026-05-11
- Local trend scan: `/last30days` returned no usable ranked evidence for the exact AKBP/protocol query. Treat that as a retrieval limitation, not proof the space is quiet.
- Follow-up sources checked: web search across GitHub, Hacker News, Reddit-indexed pages, and public project pages.
- Public themes observed:
  - persistent memory for Claude Code and tool-compatible agents
  - shared memory across multiple engineers and agents
  - local-first `.agent` style folders for portable skills and memory
  - remote tool APIs, REST APIs, dashboards, OAuth, and multi-transport access
  - knowledge graphs, temporal reasoning, contradiction detection, and source-backed memory
  - lifecycle hooks for governance, audit, redaction, and safe writes

## What similar projects are teaching users

### 1. Users understand memory through a concrete before/after

Common public framing:

- before: each agent session starts from zero
- after: the next agent can retrieve prior decisions, constraints, and failures

AKBP should keep using this language, but make the proof immediate:

- run `make demo`
- inspect `claims/claims.jsonl`
- ask for context in a new session
- see citations and source hashes

### 2. Multi-agent consistency is a stronger hook than generic memory

Several projects frame the gap as shared memory across agents, engineers, or sessions. The sharper AKBP position is:

> AKBP is not just memory. It is a portable, review-gated consistency layer for project knowledge.

That means AKBP demos should show:

- Agent A records a reviewed decision.
- Agent B retrieves it later with evidence.
- A conflicting or superseding decision is represented explicitly instead of silently overwriting history.

### 3. Tool protocols alone are not enough for portability

The market has many tool memory servers. AKBP should not compete only as another server. The useful distinction is:

- Tool protocols give agents a tool surface.
- AKBP gives tools a durable file format, schemas, audit trail, export bundle, and conformance checks.

Protocol copy should say this clearly:

> Use AKBP underneath tool protocols, hooks, CLIs, or custom runtimes when you need memory to survive tool changes.

### 4. Local-first matters, but users also expect adapters

Projects that are easier to understand expose one-liner setup, screenshots, dashboards, or adapter-specific guides.

AKBP should ship at least these user paths:

- CLI-only path: `make demo`, then manual commands.
- JSONL tool-server path: copy/paste request examples.
- Adapter-author path: capabilities, session start/end, dry-run write, approved write.
- Bundle path: export, export-check, import-check.

### 5. Safety needs to be visible, not just documented

Adjacent projects talk about governance, hooks, branch protection, audit logs, OAuth, and redaction. AKBP already has strong safety primitives, but users need to see them early.

Every public demo should include one safe failure:

- a non-approved write returns `approval_required`
- unsafe import returns a structured error
- CLI error details are redacted/truncated
- source verification flags missing or changed evidence

### 6. Users like high-level memory features, but protocol users need exact artifacts

Common features in the landscape:

- semantic search
- graph relations
- version history
- project namespaces
- memory consolidation
- dashboards
- remote access
- REST and tool-server transports

AKBP should avoid overpromising runtime features. It should emphasize artifacts that other runtimes can build on:

- claims
- evidence
- sources
- relations
- audit events
- context packs
- export manifests
- conformance reports

## Product changes this implies for AKBP

### High priority

1. **Multi-agent consistency demo**
   - Add a demo where two simulated agents operate on the same KB.
   - Agent A records a decision.
   - Agent B retrieves it and adds a superseding relation.
   - Output shows cited context and lifecycle relation.

2. **Adapter quickstart matrix**
   - One table for Claude Code, Codex-style CLI agents, Cursor-style agents, OpenClaw, and custom scripts.
   - For each: transport, setup file, session-start call, write-preview call, approval flow.

3. **Protocol vs memory server explanation**
   - Add a README block: “AKBP is the portable substrate, not another opaque memory server.”
   - Include: tool-compatible, CLI-compatible, file-backed, exportable, conformance-tested.

4. **Golden JSONL examples**
   - Add copy/paste examples for `capabilities`, `session.start`, `context`, `remember` dry-run, approved `remember`, `session.end`, `export-check`.
   - Include expected response snippets.

5. **Conflict/supersession visibility**
   - Make the lifecycle relation demo more obvious.
   - Show how a new decision supersedes an old one without deleting history.

### Medium priority

6. **Dashboard-ready summary output**
   - Add a command or example that prints object counts, latest claims, unverified sources, conformance level, and audit count.
   - Users should be able to screenshot the KB state.

7. **Import from common memory shapes**
   - Add examples converting simple tool-memory records, markdown notes, or JSONL memories into AKBP claims/sources.
   - Keep this as examples first, not a broad compatibility promise.

8. **REST and tool bridge guidance**
   - Document how AKBP can sit behind an tool-server or REST wrapper without making the reference implementation responsible for hosting every transport.

9. **Project namespace guidance**
   - Clarify how to use one KB per repo, one KB per team, or exported bundles across repos.

10. **Evaluation fixtures from real usability failures**
   - Convert early user confusion into benchmark fixtures: contradiction handling, stale source, unsafe import, missing approval, vague query retrieval.

## Positioning to use publicly

Good:

> AKBP is a local-first protocol for durable, cited agent knowledge. Agents can propose memories, humans or policy approve writes, and future sessions retrieve evidence-backed context across tools.

Also good:

> Tool servers give agents tools. AKBP gives those tools a portable memory substrate: files, schemas, source hashes, audit history, export bundles, and conformance tests.

Avoid:

- “AKBP is the best memory system.”
- “AKBP replaces existing tool protocols.”
- “AKBP is production-ready.”
- “AKBP solves all agent memory.”
- “AKBP is a vector database.”

## Immediate next artifact

Build `examples/multi-agent-consistency-demo/` with:

- `run.sh`
- `agent-a-notes.md`
- `agent-b-notes.md`
- JSONL request examples
- expected output snippets
- README explaining the story in 2 minutes

Success criteria:

- A user sees why AKBP is more than generic persistent memory.
- A tool builder sees exactly what to integrate.
- A skeptical engineer sees files, citations, safety gates, and conformance instead of vague “AI memory” claims.
