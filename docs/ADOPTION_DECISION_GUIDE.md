# Adoption decision guide

Use this guide when a new user asks whether AKBP should be a memory server, a
local context database, a repository rule file, or a portable protocol layer.

The short answer: AKBP is the portable, reviewable knowledge layer. It can sit
beside a memory server or context index, but the source of truth stays in
human-readable markdown and schema-backed JSONL artifacts.

## Pick the job first

| User job | Use AKBP when | Use another layer when |
| --- | --- | --- |
| Preserve project decisions | The decision should be cited, reviewed, exported, and reused by more than one runtime | The note is temporary session scratchpad context |
| Feed startup context to a coding agent | The next agent needs compact, cited project knowledge before planning | The agent only needs the current checkout and no durable project memory |
| Import an existing memory dump | Records need schema checks, redaction, citation review, and dry-run import before trust | The dump is private, throwaway, or will never be shared with another tool |
| Run a local retrieval index | Markdown and JSONL artifacts should remain inspectable and rebuildable | The index is the only product and portability is not required |
| Share knowledge across tools | Multiple agents need the same claims, evidence, lifecycle state, and export checks | One hosted product owns the full workflow and no tool portability is needed |
| Track stale knowledge | Old claims should be superseded or contradicted without deleting history | The only requirement is replacing a cached summary |

## Where AKBP fits

AKBP should not be the hidden memory behind an agent. The user should be able to
open the knowledge base, inspect the claims, verify the sources, and see how a
claim changed over time.

## AKBP vs a memory server

Recent agent-memory projects make persistent recall feel cheap: start a local
server, point the agent at it, and let the runtime save or search memories.
That is useful, but it answers a different question from AKBP. A memory server
optimizes runtime access. AKBP optimizes durable project knowledge that can be
reviewed, cited, exported, and moved across runtimes.

Use this split when choosing the first integration:

| Need | Prefer AKBP | Prefer a memory server or local index |
| --- | --- | --- |
| Startup context for a repo | Reviewed decisions, constraints, incidents, and architecture facts should be cited before planning | The agent only needs fast recall from one local runtime cache |
| Automatic session memory | Session summaries must be promoted through `dry_run:true`, review, and `approved:true` | The user accepts product-native or server-native memory as scratchpad context |
| Cross-agent portability | Multiple runtimes need the same inspectable files, source hashes, lifecycle states, and export checks | One host owns the agent workflow and no other tool needs to inspect the state |
| Migration from existing memory | Exports need redaction, citation review, `import-check`, and `import-apply --dry-run` before trust | The old system remains an ephemeral cache and no durable project claim is created |
| Trust after compaction | Recalled context must carry citations, lifecycle state, and budget diagnostics | A compact summary is enough and stale recall is low risk |

The practical default is not either-or. Keep fast runtime memory as a cache or
scratchpad, then promote only source-backed project facts into AKBP. If an
adapter cannot show citations, review metadata, or the exact approved write, it
should stay read-only against AKBP even if the memory server itself supports
writes.

## What useful memory looks like

Many agent-memory integrations are easy to install but hard to trust later:
they save vague summaries, hide where a fact came from, or blur temporary
scratchpad state with durable project knowledge. Treat that as the adoption
bar AKBP must clear.

Before an adapter presents recalled AKBP context as useful memory, check that
the recalled item is:

- Specific enough to change the next agent action.
- Backed by at least one citation or source id the user can inspect.
- Scoped to the selected knowledge base, such as repo-local, team-shared, or
  personal assistant memory.
- Marked with lifecycle state so stale facts can be superseded or contradicted.
- Produced from reviewed durable artifacts, not raw chat history or hidden
  product memory.
- Compact enough to fit startup context without crowding out the current task.

If a recalled item cannot pass those checks, show it as an untrusted hint or
continue without recalled memory. Do not promote it into durable AKBP state
until it has source evidence and a dry-run review path.

## Default setup choices

Start with the smallest trustworthy setup:

| Situation | Recommended setup |
| --- | --- |
| One repository, one coding agent | Repo-local AKBP knowledge base plus read-only startup context |
| One repository, multiple agents | Repo-local AKBP knowledge base plus reviewed write flow at session end |
| Team project | Team-reviewed AKBP artifacts in the repo or adjacent reviewable storage |
| Personal assistant memory | Separate private AKBP knowledge base outside public repos |
| Existing local index or memory server | Keep that system as an access layer, then export reviewed durable facts into AKBP |

The safe first integration is read-only: call capability discovery, run
`akbp.session.start` or `akbp.context`, and do not enable write methods
until the host can display dry-run previews and collect explicit approval.

When AKBP is added beside an existing memory server, local index, or tool
bridge, generate `akbp client-config` and use its `memory_server_bridge`
section as the install contract. The bridge can cache, translate, or expose
host-native tools, but durable state should remain in AKBP markdown and JSONL
artifacts. Disable or warn on integrations that store durable memory only in an
opaque bridge format, return uncited recalls, or apply writes without
`dry_run:true` preview followed by explicit `approved:true`.

When a coding agent already has product-native memory or external memory tools,
also use `native_memory_interop` from `akbp client-config`. The safe default is
to read cited AKBP context before planning, treat native memory as unreviewed
hints, and promote only sourced durable project facts through dry-run review.

Recent memory tools often optimize for fast setup, local SQLite or graph recall,
tool-protocol exposure, context-window savings, or product-native agent memory. AKBP should
not fight those layers for runtime UX. Use `memory_landscape_fit` from
`akbp client-config` to explain the split: adjacent tools can stay ephemeral or
serve low-latency recall, while AKBP remains the cited, reviewed, exportable
project-knowledge substrate.

When users ask for structured outputs, harnesses, or predictable agent memory,
also use `harness_adoption_fit` from `akbp client-config`. It turns that
preference into a setup gate: run the structured-output harness, preserve
response envelopes, citations, budget metadata, dry-run review fields, and
`error.code`, and keep AKBP read-only until those checks pass.

## What makes an integration AKBP-compatible

An integration is using AKBP as a protocol when it preserves these properties:

- The source of truth is markdown plus schema-backed JSONL artifacts.
- Retrieval includes citations or source references.
- Writes can be previewed with `dry_run:true`.
- Durable writes require request-level `approved:true` or an explicit trusted local policy.
- Stale knowledge is superseded or contradicted instead of silently overwritten.
- Export and import checks can run before another tool trusts the bundle.
- The export and import checks are part of the user-visible trust path, not a hidden adapter detail.

If an integration only stores opaque memories and returns uncited summaries, it
may still be useful, but it is not delivering the AKBP trust model.

## Ten-minute adoption path

1. Run `make demo` to see the review-gated flow.
2. Read `docs/GETTING_STARTED.md` to choose knowledge-base scope.
3. Run `examples/adoption-preflight/run.sh` to verify the first-run trust gate.
4. Use `akbp client-config --profile read-only` for the first adapter setup.
5. Enable reviewed writes only after the host can show `review_required`,
   `apply_instruction`, planned writes, warnings, and skipped records.
6. Add export or import checks before moving knowledge across tools.

The adoption goal is simple: a real user should understand what will be stored,
why it is trusted, how it can be reviewed, and how another runtime can consume
it without custom glue.
