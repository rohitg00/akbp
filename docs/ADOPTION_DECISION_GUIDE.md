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
