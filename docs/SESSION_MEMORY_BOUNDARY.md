# Session Memory Boundary

Use this guide when an agent runtime has its own session notes, scratchpad,
chat summary, local cache, or private memory store and needs to decide what
belongs in AKBP.

AKBP should be the durable, reviewed project knowledge layer. Runtime session
state can still exist, but it is not the source of truth for decisions another
agent should trust later.

## Boundary model

| Layer | Purpose | Lifetime | AKBP operation |
|-------|---------|----------|----------------|
| Runtime scratch | Reasoning, command output, failed attempts, UI state, temporary todo lists | Current session only | No AKBP write |
| Session summary | Concise end-of-session facts the runtime proposes for review | Until reviewed or discarded | `akbp.session.end` with `dry_run:true` |
| Durable project knowledge | Approved decisions, workflows, constraints, blockers, preferences, and source-backed facts | Across sessions and tools | Repeat the reviewed request with `approved:true`, then refresh retrieval |
| Rebuildable local state | Search indexes, caches, and runtime-specific acceleration data | Rebuildable | `akbp.index` or runtime-owned upkeep |

This separation keeps AKBP useful beside memory servers, repository instruction
files, tool-protocol hosts, editor rules, and chat history. Those systems can
hold transient context. AKBP holds portable artifacts that can be inspected,
exported, checked, imported, cited, superseded, or contradicted.

## Promotion rule

Promote session state into AKBP only when all of these are true:

- The content will still matter to a future agent working on the project.
- The content is scoped to this project or explicitly belongs in this knowledge base.
- The content is concise enough to retrieve later without dragging in the whole session.
- The content is backed by a source, transcript summary, command result, or reviewed user statement.
- The runtime can show the dry-run preview, including `review_required`, `apply_instruction`, warnings, source ids, skipped records, and would-write paths.
- The apply request repeats the reviewed method, path, and params with `approved:true`.

Keep content out of AKBP when it is only scratch reasoning, a raw transcript,
private chat, a credential, a copied log dump, a speculative guess, or a
runtime-specific cache entry.

## Adapter workflow

At session start:

```json
{"id":"caps","method":"akbp.capabilities"}
{"id":"start","method":"akbp.session.start","path":".","params":{"task":"continue release work","limit":5,"max_chars":4000}}
```

During the session, keep transient scratch in the runtime. If new source
material matters, register or ingest it through a preview-first flow instead of
copying it into a private memory file.

At session end, write a concise local summary containing only durable
candidates, then preview crystallization:

```json
{"id":"end-preview","method":"akbp.session.end","path":".","dry_run":true,"params":{"transcript":"session-summary.md","apply":true}}
```

If the preview is approved, apply the same request and refresh retrieval:

```json
{"id":"end-apply","method":"akbp.session.end","path":".","approved":true,"params":{"transcript":"session-summary.md","apply":true}}
{"id":"index","method":"akbp.index","path":".","approved":true,"params":{"incremental":true}}
```

If the preview is not approved, discard or revise the session summary. Do not
silently keep an alternate durable memory store as the project truth.

## Review checklist

Before applying session memory, check:

- Does each proposed claim describe a durable decision, workflow, blocker,
  preference, or project fact?
- Does it avoid secrets, auth material, private DMs, raw transcript text, and
  copied command logs?
- Does it cite source ids or derive from the reviewed transcript summary?
- Would a different runtime understand the record without the original chat?
- If it replaces old knowledge, should the adapter use `akbp.supersede` or
  `akbp.contradict` instead of adding a competing claim?

The default answer for uncertain session state is to keep it transient. AKBP is
valuable because durable writes are reviewed, cited, and auditable.
