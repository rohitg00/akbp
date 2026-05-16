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

## AKBP vs plain markdown or token cache

Plain markdown and runtime token caches are useful. A project-understanding
markdown file is often the fastest scratchpad for a single agent, and a built-in
cache can reduce repeated context cost inside one host. AKBP should not replace
those paths when the user only needs temporary recall.

Use `memory_landscape_fit.plain_markdown_cache_comparison` when an installer or
reviewer asks why AKBP is more than a markdown file or cache. The split is:

| Need | Plain markdown or cache is enough | AKBP adds value when |
| --- | --- | --- |
| Scratchpad context | One runtime needs a temporary summary | Future agents must see cited project decisions before planning |
| Speed | The host only needs faster local recall | The memory must survive host changes and export/import review |
| Updates | Replacing the latest summary is acceptable | Stale facts need supersede or contradict lifecycle records |
| Trust | The user can manually inspect one note | Writes need `dry_run:true`, explicit `approved:true`, audit output, and source ids |

The minimum proof is concrete: `akbp.session.start` returns bounded cited
context, an unapproved durable write fails with `error.code approval_required`,
and `export-check` verifies the markdown and JSONL artifacts without adapter
local state.

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

When a tool claims Git-backed or version-controlled agent memory, use
`memory_landscape_fit.git_reviewable_promotion_flow`. Git should be the review
and distribution layer for AKBP artifacts, not the thing that turns uncited
summaries into durable truth. The safe path is: select one KB scope, register
evidence, preview the write with `dry_run:true`, review the AKBP artifact diff,
repeat the same request with `approved:true`, then run `export-check` or
conformance before another runtime trusts the memory.

For each row coming from an existing memory server, use
`memory_server_bridge.external_memory_promotion.promotion_triage` before
import or write preview. It maps rows into runtime scratch, evidence-seeking
hints, reviewable durable candidates, or blocked private/secret content, and it
requires the adapter to emit a class, action, source-reference status,
review-surface status, and reason. Missing classification or missing citations
for a durable candidate should fail closed instead of becoming a prompt-only
judgment.

If the host has a formal memory-capability registry, also use
`host_capability_descriptor.tool_protocol_memory_capability`. It gives
installer-safe labels and the minimum semantics a host must preserve before it
advertises AKBP as memory: local artifacts as source of truth, cited startup
recall, reviewed writes, structured errors, budget fields, and exportable
state. If the registry cannot express those semantics, register only read-only
startup context tools.

When a coding agent already has product-native memory or external memory tools,
also use `native_memory_interop` from `akbp client-config`. The safe default is
to read cited AKBP context before planning, treat native memory as unreviewed
hints, and promote only sourced durable project facts through dry-run review.

Recent memory tools often optimize for fast setup, local SQLite or graph recall,
tool-protocol exposure, context-window savings, or product-native agent memory. AKBP should
not fight those layers for runtime UX. Use `memory_landscape_fit` from
`akbp client-config` to explain the split: adjacent tools can stay ephemeral or
serve low-latency recall, while AKBP remains the cited, reviewed, exportable
project-knowledge substrate. Use
`memory_landscape_fit.context_pressure_triage` when startup recall competes
with the current task for context budget. The adapter should classify the
result as trusted bounded context, narrower retrieval needed, untrusted hint, or
no-memory path. If citations, scope fingerprints, warnings, or budget fields do
not survive, continue from repository source of truth instead of filling the
prompt with broad memory. Use
`memory_landscape_fit.feature_claim_audit` when an adapter advertises semantic
recall, graph memory, context-window savings, multi-agent sharing, or local-first
safety. Those claims should become concrete checks: cited context plus a runnable
search or benchmark proof, preserved budget diagnostics, one selected
`knowledge_base.path`, export-checkable artifacts, and an `approval_required`
failure before any approved write path is enabled. Use
`memory_landscape_fit.memory_control_claim_gate` when a host advertises automatic
or self-improving memory writes. The host should prove the reviewed promotion
sequence: dry-run preview, visible review of evidence and artifact paths,
explicit human approval or trusted local policy, exact `approved:true` replay,
and an audit event before another runtime trusts the new memory. Use
`memory_landscape_fit.compaction_survival_claim_gate` when a host claims memory
survives compaction, truncation, or restart. The host should run cited
`akbp.session.start` recovery, preserve warnings and budget diagnostics, record
which AKBP items influenced the plan, and pass the `compaction-handoff-recall`
benchmark before planning from recovered memory. Use
`memory_landscape_fit.coding_agent_reliability_gate` when a user is taking over
an inherited repo, running parallel agent sessions, switching hosts or models,
or reporting inconsistent coding-agent output. The host should run discovery,
read-only doctor, cited `akbp.session.start` with warnings treated as blockers,
and a context-use report before planning from recalled memory. Durable findings
still need dry-run review and exact `approved:true` replay. Use
`memory_landscape_fit.install_friction_checks` when a user asks why AKBP is not
just another local memory server: the first-run proof should show no Docker or
cloud account requirement, one selected KB shared across clients, and a
read-only setup until the host preserves citations, envelopes, and review
metadata.

Use `memory_landscape_fit.local_first_adoption_probe` before making local-first
positioning claims in an installer or adapter UI. The probe maps the claim to
commands a user can actually run: `akbp discover`, `akbp doctor --profile
read-only`, `akbp client-config --profile read-only`,
`./examples/structured-output-harness/run.sh`, and an `export-check` against
the selected knowledge base. If any step hides `error.code`, drops citations,
stores durable memory only in an opaque sidecar database, or cannot verify the
exported artifacts, keep AKBP read-only and treat adjacent memory tools as
ephemeral hints.

When users ask for structured outputs, harnesses, or predictable agent memory,
also use `harness_adoption_fit` from `akbp client-config`. It turns that
preference into a setup gate: run the structured-output harness, preserve
response envelopes, citations, budget metadata, dry-run review fields, and
`error.code`, and keep AKBP read-only until those checks pass.

When tool-protocol or JSONL output threatens to crowd out the task, treat raw
tool responses and audit logs as evidence or diagnostics, not startup context.
The adapter should call `akbp.session.start` or `akbp.context` with a narrow
task, `require_citations:true`, and a bounded `max_chars`; then surface the
returned `budget` fields. The `tool-output-context-budget` fixture checks this
path so a host can prove compact cited context before claiming context-window
savings.

When an editor, workflow tool, or coding agent has an active file, component,
workflow, or selected node, use `workflow_context_selector` from `akbp client-config`
before planning. The adapter should pass the active selection into scoped
`akbp.session.start`, require citations and budget metadata, rerun retrieval
when the selection changes, and continue without recalled AKBP memory when the
scoped context is empty, uncited, warning-bearing, or truncated.

Use `structured_output_repair` from `akbp client-config` when wiring retries.
Adapters may repair malformed JSON, request envelopes, unsupported methods after
capability refresh, or invalid params using `error.details.params_schema`. They
must not treat approval failures, uncited startup context, unsurfaced warnings,
budget truncation, source drift, or rejected imports as retryable prompt issues.
The repair map caps local repair at one attempt per request fingerprint, so a
host that still fails after the local fix must surface the structured error
instead of looping or asking the model to reinterpret it.
After any params repair on a write-capable method, rerun `dry_run:true` and
collect a fresh review before `approved:true`.

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
