# AKBP with Obsidian

Obsidian is a good human interface for an AKBP knowledge base because AKBP stores durable knowledge as local files. The useful split is simple:

- Obsidian is for humans reading, reviewing, and editing notes.
- AKBP is for agents reading and writing structured memory safely.

AKBP does not replace Obsidian. It gives agents a contract for the parts of a vault that should be treated as durable memory.

## Recommended vault layout

Use an AKBP knowledge base inside a vault, or point Obsidian at an existing AKBP directory. A complete small example lives in `examples/obsidian-vault/`.

```text
obsidian-vault/
  AKBP.md
  akbp.json
  claims/
    claims.jsonl
  raw/
    sources/
      sources.jsonl
  wiki/
    decisions/
    imports/
  logs/
    audit.jsonl
```

Humans can browse `AKBP.md`, `wiki/`, and imported source pages in Obsidian. Agents should write through the AKBP CLI or JSONL tool server so writes stay structured, reviewable, and auditable.

## What agents should store

Good AKBP memories are small durable claims with evidence:

- project decisions
- coding conventions
- user preferences
- source-backed research findings
- release risks
- adapter lifecycle notes
- recurring workflow instructions

Avoid storing raw private chat logs as memory. Prefer summaries, claims, source references, and citations.

## Safe write flow

Start write-capable operations with a dry run:

```bash
akbp --path ./obsidian-vault ingest ./meeting-notes.md --type transcript --dry-run
```

Then apply only after review:

```bash
akbp --path ./obsidian-vault ingest ./meeting-notes.md --type transcript
```

For JSONL tool server integrations, use request-level `dry_run:true` first, then repeat with `approved:true` only after the preview is reviewed.

## Session lifecycle flow

At agent startup, retrieve relevant vault memory:

```json
{"id":"start","method":"akbp.session.start","path":"./obsidian-vault","params":{"task":"ship the release checklist","limit":5}}
```

At shutdown, preview session crystallization before writing:

```json
{"id":"end-preview","method":"akbp.session.end","path":"./obsidian-vault","dry_run":true,"params":{"transcript":"session.md","apply":true}}
```

Only apply after review:

```json
{"id":"end-apply","method":"akbp.session.end","path":"./obsidian-vault","approved":true,"params":{"transcript":"session.md","apply":true}}
```

## Why not just vectorize the vault?

Vector search over Markdown can retrieve useful context, but it does not tell an agent:

- which statements are durable claims
- which source supports a claim
- whether a claim was superseded
- whether a write was reviewed
- whether another agent can import the memory safely

AKBP adds that contract while keeping the files local and readable.

## Good public positioning

Use this framing:

> Obsidian is great for human memory. AKBP makes the durable parts of a vault agent-readable: claims, sources, citations, import/export, and review-gated writes.

Do not frame AKBP as an Obsidian replacement. It is the memory contract underneath tools like Obsidian, coding agents, and local retrieval systems.
