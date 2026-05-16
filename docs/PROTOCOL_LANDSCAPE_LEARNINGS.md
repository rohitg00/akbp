# Protocol landscape learnings

This note tracks public signals from adjacent agent-memory and agent-harness projects and turns them into AKBP usability work.

It is not a vendor ranking. It is a product checklist for making AKBP easier for real users to understand, run, and adopt.

## Research input

This synthesis is based on recent public signals from developer-tooling, agent-memory, and documentation-workflow discussions. Keep the repo artifact focused on reusable patterns, not vendor names or source-by-source research notes.

Public themes observed:
  - persistent memory for coding agents and tool-compatible runtimes
  - shared memory across multiple engineers and agents
  - local-first `.agent` style folders for portable skills and memory
  - local-first memory servers that are easy to start but still require users
    to decide which durable memory scope the agent should trust
  - portable agent-memory protocol discussions that emphasize transfer,
    provenance, and privacy across heterogeneous runtimes
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

Recent lightweight research reinforced a practical adapter gap: many adjacent
agent-memory projects expose a server or bridge surface, but client guidance
often stops at transport setup. AKBP should keep showing adapter authors the
control-flow contract: discover capabilities, branch on `ok` and
`error.code`, preview write-capable calls with `dry_run:true`, stop on
`approval_required`, and only repeat the same reviewed method, path, and params
with `approved:true` after approval or trusted local policy.

The latest scan also reinforced a context-budget point: tool-protocol hosts can
pay real prompt cost for every exposed method schema. AKBP adapters should not
publish every memory and write method by default. Discovery and generated client
configs should make the least-privileged method set explicit, start from the
read-only allowlist, and expose write-capable schemas only after capability,
doctor, harness, and review-surface checks pass.

Recent tool-protocol and coding-agent memory discussions keep returning to
context bloat: users want durable recall, but they do not want every memory
server, rule file, or tool schema to silently expand the startup prompt. AKBP
now exposes a retrieval `budget_contract` through capability discovery so
adapter authors know to pass `max_chars`, preserve `budget.*` and
`quality.*` fields, and fail closed when a host bridge hides clipped-memory
warnings.

The newest bridge-oriented scan reinforced a second adapter issue: some hosts
classify integrations through a generic memory-capability registry rather than a
custom AKBP-aware adapter. AKBP should give those hosts a compact projection
that says exactly what can be mapped safely: durable project knowledge, cited
startup reads, read-only default methods, disabled direct writes, and
`dry_run` plus exact `approved:true` replay for reviewed writes. If the host
cannot preserve citations, `error.code`, context budgets, and review metadata,
the projection should fail closed to startup-context tools only.

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
   - One table for terminal agents, editor agents, local assistants, and custom scripts.
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
   - Shipped in `akbp status` and `akbp.status`.
   - Prints object counts, latest claims, source verification health, conformance level, index presence, and audit count.
   - Gives adapters and future dashboards a stable payload before building a hosted UI.

7. **Import from common memory shapes**
   - Add examples converting simple tool-memory records, markdown notes, or JSONL memories into AKBP claims/sources.
   - Keep this as examples first, not a broad compatibility promise.

8. **REST and tool bridge guidance**
   - Document how AKBP can sit behind a tool-server or REST wrapper without making the reference implementation responsible for hosting every transport.

9. **Project namespace guidance**
   - Clarify how to use one KB per repo, one KB per team, or exported bundles across repos.
   - Make that scope choice machine-readable in generated adapter config so a
     runtime does not silently blend repo-local, team-shared, personal, and
     migration memory.

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

## Shipped artifact: multi-agent consistency demo

`examples/multi-agent-consistency-demo/` now shows:

- Agent A recording a durable decision with evidence.
- Agent B retrieving cited context before acting.
- Agent B superseding the old decision with a more precise validation-backed decision.
- Level 3 conformance confirming lifecycle relations.

Success criteria:

- A user sees why AKBP is more than generic persistent memory.
- A tool builder sees the retrieval and supersession path.
- A skeptical engineer sees files, citations, safety gates, and conformance instead of vague “AI memory” claims.

## Shipped artifact: adapter quickstart matrix

`docs/ADAPTER_AUTHOR_QUICKSTART.md` now includes a matrix for choosing the first
integration path across terminal agents, editor agents, local assistants, custom
scripts, and hosted tool bridges.

The matrix keeps the user-value lesson concrete:

- start read-only when evaluating a runtime
- use `akbp.session.start` for startup context
- preview write-capable calls with `dry_run:true`
- require an explicit approval surface before `approved:true`
- keep hosted or autonomous bridges read-only until their trust boundary is documented

## Shipped artifact: canonical JSONL quickstart

`examples/jsonl-quickstart/` turns the tool-server adoption story into one
runnable sequence for adapter authors:

- discover capabilities and required profiles
- retrieve cited startup context before planning
- preview a durable write with `dry_run:true`
- reject an unapproved write with `approval_required`
- apply the same memory only with `approved:true`
- refresh retrieval, recall cited context, and export a portable bundle
- capture an `adapter-contract.json` trace manifest with the response fields,
  hard stops, and validation command a bridge must preserve

This addresses the low-friction setup lesson from adjacent memory tools without
weakening AKBP's review-gated protocol boundary.

## Shipped artifact: client config scope selection

`akbp client-config` now emits `scope_selection`, a first-run trust-boundary
contract for adapter installers:

- repo-local KB as the safe default
- team-shared KB when reviewed project knowledge is intentionally shared
- personal-assistant KB outside public repos for private user/workflow memory
- migration KB for reviewed imports from existing notes or memory exports

This turns the research-backed adoption gap into setup data: before an adapter
trusts recalled context, it can show which AKBP path is selected, what belongs
there, what must stay out, and why write-capable flows remain blocked until
dry-run review and approval exist.

## Shipped artifact: tool schema budget contract

`akbp discover` and `akbp client-config` now emit `tool_schema_budget`, a
profile-aware contract for host tool exposure:

- publish only the selected profile's methods
- keep write-capable schemas blocked until reviewed-write preflight passes
- use `akbp.capabilities` for discovery instead of pasting every method into
  the model prompt
- request bounded startup context before planning from recalled memory

This keeps AKBP adapter setup aligned with recent tool-protocol guidance:
memory should be available on demand, but schema exposure itself must remain
bounded and review-aware.

## Shipped artifact: compaction handoff recall proof

Recent agent-memory discussions keep circling the same failure mode: long coding
sessions get compacted, then the next agent resumes from stale or uncited memory.
AKBP now has a focused benchmark fixture for that gap:
`benchmarks/fixtures/compaction-handoff-recall/`. It proves a startup handoff can
retrieve the current cited snapshot with absolute dates, lifecycle status, and a
review-gated write policy while preserving the superseded relative-date memory as
history instead of answer material.

## Shipped artifact: structured output harness example

Recent adapter discussions keep pointing at a practical gap: structured output
is only useful when clients actively validate it. AKBP now ships
`examples/structured-output-harness/` as a runnable quality gate for adapter
authors.

The example checks the JSONL response envelope, capability negotiation,
`akbp.doctor` readiness, cited startup context, dry-run review metadata, and
the structured `approval_required` error before any adapter trusts memory or
enables durable writes.

This turns the benchmark fixture into a user-facing adoption path: copy the
harness, keep read paths strict, and fail closed on response shape or approval
contract drift.

## Shipped artifact: bounded context budget diagnostics

Recent tool-protocol discussions reinforced that agents burn context when every
startup flow pastes full tool definitions, wiki pages, or raw memory records.
AKBP already supports `max_chars` on `akbp.context` and `akbp.session.start`;
the budget payload now makes partial context machine-readable by separating
clipped summaries from omitted items and reporting item counts before and after
budgeting.

This gives low-context adapters a concrete control signal: trust cited bounded
context when it fits, lower `limit` or ask for more budget when important items
were omitted, and surface warnings without parsing prose.

## Shipped artifact: source provenance gate for adapter writes

Recent memory-server discussions keep showing the same adoption risk: quick
local setup is attractive, but users ask what backs the stored facts. AKBP's
generated adapter prompt contract now includes
`source_provenance_gate`, a machine-readable rule that blocks adapters from
promoting unsupported chat memory, cache entries, or model summaries into
durable AKBP claims.

The gate tells adapters to preview writes only when the claim is backed by an
existing source id, cited startup/context evidence, `akbp.cite`, or source
material registered with `akbp.source.add`. If that backing is missing, the
adapter keeps the observation as runtime scratch instead of creating durable
project memory.

## Shipped artifact: KB scope guidance

Recent local and tool-compatible memory projects keep converging on shared
profiles, sidecar transcript ingestion, graph-backed memory, and hosted or local
runtime bridges. The practical AKBP lesson is that users need to choose the
trusted knowledge-base scope before they connect an adapter.

`docs/GETTING_STARTED.md` and `docs/ADAPTER_AUTHOR_QUICKSTART.md` now describe
safe defaults for repo-local, team-shared, personal assistant, transcript
sidecar, and migration use cases.

The guidance keeps AKBP's distinction clear:

- repo-local KBs are the default for project work
- personal KBs stay outside public repos
- team KBs require approved, cited knowledge
- transcript sidecars propose reviewed claims instead of importing raw logs
- migrations use import checks and staging before writes

## Added research track: spec-driven agent development kits

Spec-driven development kits are adjacent to AKBP even when they are not memory systems. The reusable pattern is that agent work improves when intent, constraints, plans, and tasks become durable reviewable artifacts before code or automation runs.

### Why this matters

Spec-driven agent workflows solve a different but related problem:

- They turn intent into durable project artifacts before code is written.
- They give coding agents a staged workflow instead of one giant prompt.
- They make the human review boundary explicit between phases.
- They produce files that can be versioned, inspected, reused, and handed between agents.

That is close to AKBP's core job: turn useful agent context into durable, inspectable project knowledge.

### Pattern signals

Observed public pattern:

- Framing: open source toolkit for spec-driven development with coding agents.
- Core flow: project rules -> user intent -> technical plan -> task list -> implementation.
- User promise: stop vague prompt-driven development; make specifications living artifacts that drive implementation.
- Integration style: installed CLI plus agent-facing commands/templates.
- Strongest product lesson: the workflow is memorable because each phase has a named artifact and a clear gate.

### What AKBP should learn from this category

1. **Name the workflow stages, not just the methods**
   - Users remember named stages better than raw method names.
   - AKBP should expose a similarly human-readable path:
     - discover evidence
     - preview memory
     - approve write
     - retrieve cited context
     - supersede stale knowledge
     - export bundle

2. **Make durable artifacts feel first-class**
   - Specs, plans, and tasks work because users see them as product artifacts.
   - AKBP should make claims/sources/context packs/audit events feel like the product, not internal implementation details.

3. **Add phase gates to demos and docs**
   - AKBP already has dry-run and approval gates.
   - The docs should frame them as a user workflow, not only as safety mechanics:
     - proposed knowledge
     - reviewed knowledge
     - active knowledge
     - superseded knowledge

4. **Create agent-facing commands that map to user language**
   - Tool methods are useful for integrations, but humans need memorable commands.
   - Candidate public demo language:
     - `akbp capture`
     - `akbp review`
     - `akbp recall`
     - `akbp supersede`
   - This can stay as documentation first before adding CLI aliases.

5. **Ship templates, not only reference docs**
   - Agent workflow kits spread when people can initialize scaffolding quickly.
   - AKBP should offer starter templates:
     - `project-memory-template`
     - `release-memory-template`
     - `adapter-author-template`
     - `multi-agent-consistency-template`

6. **Treat project rules as a first-class artifact**
   - AKBP could define a lightweight `AKBP.md` section for project memory rules:
     - what counts as durable knowledge
     - who can approve writes
     - what must never be stored
     - when to supersede vs contradict
     - required evidence quality

7. **Make implementation tasks come from knowledge gaps**
   - Staged agent workflows turn planning artifacts into tasks.
   - AKBP can turn missing/contested/stale knowledge into tasks:
     - verify source hash
     - resolve contested claim
     - add evidence for uncited claim
     - supersede stale workflow
     - export reviewed bundle

### New AKBP artifact ideas from this track

High-value, low-risk docs/examples:

1. `docs/AKBP_WORKFLOW.md`
   - A named workflow from evidence -> reviewed memory -> recall -> lifecycle update.

2. `examples/multi-agent-consistency-demo/`
   - Shows Agent A recording a decision and Agent B retrieving/superseding it.

3. `templates/project-memory-rules/AKBP.md`
   - Starter rules for what agents should and should not store.

4. `docs/TEMPLATES.md`
   - Explains starter memory templates and when to use each.

5. `benchmarks/fixtures/knowledge-gap-to-task/`
   - Converts missing evidence, contested claims, or stale sources into actionable tasks.

## Shipped artifact: project memory rules template

`templates/project-memory-rules/AKBP.md` now gives new repositories a copyable local rule file before agents start writing durable memory.

## Shipped artifact: bridge adoption checklist

Recent research keeps showing tool-compatible memory projects that make setup
easy but blur the durability boundary. `docs/TOOL_PROTOCOL_BRIDGE.md` now
includes an adoption checklist for evaluating memory-server bridges before a
runtime treats them as trusted AKBP memory.

The checklist keeps the comparison concrete:

- durable knowledge stays in AKBP files, not bridge-owned state
- bridge tools start from `akbp.capabilities` and generated client config data
- startup context must be cited before it influences planning
- direct write methods stay blocked until dry-run preview and approval UI exist
- hosts preserve `ok`, `error.code`, warnings, and budget fields
- export and import checks still work without bridge-local metadata

`akbp discover` and `akbp client-config` now also expose
`external_memory_promotion.intake_classification`, because recent
tool-compatible memory projects make it easy to accumulate mixed runtime memory
but do not always tell adapters which rows are safe durable knowledge. The classifier
separates runtime scratch, ephemeral hints, source-backed durable candidates,
and blocked private or secret-like rows before any `import-check` or dry-run
preview happens.

It covers:

- durable knowledge criteria
- acceptable evidence
- `dry_run:true` preview and `approved:true` apply requirements
- approval policy
- secret and private-data exclusions
- lifecycle handling for superseded or contradicted knowledge
- validation commands
- adapter boundaries

`docs/TEMPLATES.md` explains when to use the template and how to adopt it after `akbp init`.

## Shipped artifact: knowledge-gap-to-task fixture

Lightweight research on recent agent-memory tooling again showed that adoption
depends on visible setup, project scope, shared context, and immediate retrieval
value. AKBP should not answer that only with more adapter glue. The stronger
move is to keep product decisions evidence-backed:

- cite the research or user signal
- name the concrete AKBP gap
- choose the next smallest product task
- preserve the evidence chain for later review

`benchmarks/fixtures/knowledge-gap-to-task/` now captures that loop as a
repeatable fixture. It verifies that a research-backed adoption gap can become a
cited, reviewable product task before write-capable transports or runtime-specific
adapter work expands the surface area.

### Positioning update

Spec-driven agent workflows are proving that users want explicit durable artifacts and checkpoints. AKBP should borrow that packaging:

> Spec-driven development makes product intent executable. AKBP makes project knowledge portable, reviewable, and reusable across agent sessions.

This keeps AKBP distinct while learning from the adoption mechanics of staged agent workflows.

## Added research track: rich review artifacts

Rohit pointed at a current agent-output pattern that fits AKBP well. The useful lesson is not any specific brand, author, or implementation. The reusable pattern is this:

> Agents should compile messy context into portable, cited, interactive review artifacts, not only linear markdown summaries.

### Why this matters for AKBP

AKBP's source of truth is structured and file-backed: claims, sources, source hashes, relations, audit events, and context packs. That is exactly the substrate needed for rich artifacts that humans can review and future agents can reuse.

A good artifact is not the source of truth. It is a generated view over AKBP data.

### High-value AKBP artifact formats

- decision review page
- agent handoff page
- pull request understanding page
- postmortem page
- research map page
- release readiness page

These should be self-contained, static-first HTML files generated from AKBP objects.

### Product lesson

Markdown is still useful for durable notes, but complex knowledge often needs structure:

- diagrams
- timelines
- annotated diffs
- severity colors
- collapsible source snippets
- relation maps
- review checklists
- export buttons for proposed updates

AKBP can own the trust layer while the HTML artifact owns the review surface.

### Safety lesson

Rich artifacts must not become a bypass around review-gated writes.

Rules:

- no network calls by default
- no secrets or private dumps
- proposed updates export as JSONL
- existing `import-check` validates before apply
- existing approval gates apply before durable writes
- artifacts cite source ids and hashes

### Concrete next artifact

Build `examples/rich-context-artifact/`:

1. create a small KB with a source note, claims, and lifecycle relation
2. generate `agent-handoff.html`
3. include cited claims and source ids
4. export selected proposed updates as `updates.jsonl`
5. run `import-check` before any apply

This gives AKBP a very clear public demo:

> AKBP is the source of truth. Rich artifacts are the review surface.

See `docs/RICH_CONTEXT_ARTIFACTS.md` for the implementation sketch.

## Added research track: host install profiles

Recent scans still show agent-memory projects competing on quick host setup:
tool-protocol servers, local memory caches, graph-backed stores, and hosted
bridges all try to make the first integration feel like a one-command install.
The adoption gap for AKBP is not another memory server claim. It is giving
installers enough machine-readable setup shape to keep AKBP as the durable,
reviewable substrate while hosts expose familiar tools.

### Product lesson

Adapter installers need host-specific copy without weakening the trust model:

- terminal agents need pasteable discovery, doctor, and client-config commands
- editor agents need a host tool manifest, not hand-written method lists
- existing memory servers need a migration or promotion boundary so runtime
  caches do not become durable project truth

### Shipped artifact: host install profiles

`akbp client-config` now includes `host_install_profiles` for terminal agents,
editor agents, managed tool-protocol hosts, and existing memory-server runtimes.
Each profile states the safe default profile, concrete setup commands or
manifest steps, first AKBP tool to call, and the condition required before
writes can be enabled.

Recent managed tool-runtime signals make that extra profile useful: a hosted
environment can expose familiar tools quickly, but AKBP should still start with
read-only cited context and keep durable writes blocked until the host proves a
separate approval surface outside autonomous tool execution.

Success criteria:

- adapter installers can show a clear under-ten-minute setup path
- read-only cited context remains the first enabled capability
- write-capable flows stay gated on dry-run review or migration checks

## Shipped artifact: verified rich context artifact gate

Recent scans continue to show memory tools competing on quick setup and shared
recall. AKBP's stronger product story is that durable knowledge can also power
human review surfaces without letting those surfaces become hidden write paths.

`examples/rich-context-artifact/run.sh` now turns that story into a runnable
gate. It validates the static handoff artifact's JSONL proposals, previews the
import, applies only with explicit approval, verifies the source hash, recalls
the claims with required citations, and checks an export bundle.

This keeps the rich artifact path honest:

- HTML is a generated review surface
- JSONL proposals remain the write boundary
- source hashes and citations survive the apply path
- portable exports still validate without artifact-local state

## Shipped artifact: host memory capability mapping

Recent tool-protocol and memory-server discussions are moving toward explicit
memory capability labels. The adoption risk for AKBP is that a host marks it as
generic memory and loses the properties that make it trustworthy.

`akbp client-config` now includes
`host_capability_descriptor.tool_protocol_memory_capability`. It gives host
registries safe labels plus the required semantics: AKBP artifacts remain the
source of truth, startup recall must be cited, writes stay review-gated,
structured errors and budget fields are preserved, and export/import checks do
not depend on host-local memory state.
`memory_capability_registration_manifest` is the compact registration form for
hosts that only accept a generic memory capability: advertise AKBP as durable
project knowledge only when citations, source ids, envelopes, budgets, and the
review boundary survive the host mapping.

If a host registry cannot express those semantics, the safe integration is
read-only startup context tools, not a generic automatic memory store.

## Shipped artifact: install friction checks

The latest lightweight scan found the same pull from several adjacent memory
tools: local setup should feel cheap, often framed as no Docker, no API keys,
one binary or server, and shared memory across multiple coding clients.

AKBP should meet that setup bar without copying the unsafe part of the pattern.
`akbp client-config` now exposes
`memory_landscape_fit.install_friction_checks` so installers can answer three
first-run questions before positioning AKBP as memory:

- can the user start locally without Docker, a cloud account, API keys, or a
  hosted database?
- can multiple clients share the same selected KB without creating hidden
  per-client durable stores?
- can setup stay read-only until citations, response envelopes, and review
  metadata are preserved?

The current scan also found a sharper comparison problem: adjacent memory tools
often advertise semantic recall, graph memory, token savings, shared memory, or
local-first safety as feature claims. The latest scan adds one more common
shortcut: treating a tool-protocol memory server as sufficient durable
project memory just because it exposes persistent tools. AKBP should turn those
claims into verifiable adapter gates instead of accepting them as positioning
copy.
`memory_landscape_fit.feature_claim_audit` now maps those claims to checks for
cited context, runnable search or benchmark proof, preserved context budget
diagnostics, one selected KB path, tool capability discovery, export-checkable
artifacts, and an `approval_required` stop before writes are enabled.

Recent Git-backed memory positioning adds a sharper adoption question: can a
team review agent knowledge like code without losing citations, lifecycle
state, and approval gates? `memory_landscape_fit.git_reviewable_promotion_flow`
turns that into a machine-readable sequence for adapters: choose one KB scope,
register evidence, preview with `dry_run:true`, review the AKBP markdown and
JSONL artifact diff in Git, apply the exact reviewed request with
`approved:true`, and verify the resulting bundle before another runtime trusts
it. This keeps Git responsible for review and distribution while AKBP remains
responsible for source-backed durable knowledge.

## Shipped artifact: context efficiency claim gate

Recent tool-protocol memory positioning also leans on context-window savings:
serve compact tools, return bounded results, and avoid loading full memory into
the prompt. AKBP should support that claim only when the adapter proves it.

`akbp client-config` now exposes
`memory_landscape_fit.context_efficiency_claim_gate`. The gate requires a
bounded `akbp.session.start` request, preserved budget fields, citations that
survive budgeting, quality metadata, and surfaced warnings. If a host drops
budget fields, strips citations during summarization, or claims token savings
without showing `original_summary_chars` and `summary_chars`, the integration
must fail closed and avoid marketing AKBP as context-efficient for that host.

The current scan also showed the sharper product question: when memory and the
current task compete for context budget, the adapter needs a decision map, not
more prose. `akbp client-config` now exposes
`memory_landscape_fit.context_pressure_triage`. It classifies recalled context
as trusted bounded context, narrower retrieval needed, untrusted hint, or no
memory path. The fail-closed rule is deliberately plain: preserve citations,
scope fingerprints, quality, warnings, and budget metadata, or continue from
repository source of truth without recalled memory.

Success criteria:

- quick-start UX stays competitive with local memory servers
- trust still comes from cited, reviewed AKBP artifacts
- installers have machine-readable checks instead of prose-only positioning

## Shipped artifact: temporal graph claim gate

The latest scan also surfaced another recurring pitch from adjacent memory
tools: temporal or knowledge-graph recall for coding agents. That is useful as
an access pattern, but it is not enough by itself to make memory trustworthy.

`akbp client-config` now exposes
`memory_landscape_fit.temporal_graph_claim_gate`. The gate requires graph-backed
claims to stay connected to cited source ids, lifecycle status, relation records,
audit or export metadata, and runnable checks before an installer describes AKBP
as graph-capable project memory. It points adapters at Level 3 conformance,
export-check, the `graph-jsonl-records` benchmark fixture, and cited
`akbp.context` retrieval.

If a host can only return graph entities or edges from an opaque memory server,
the safe positioning is narrower: treat that graph as an ephemeral index and
trust only AKBP claims, lifecycle links, citations, and export-checkable JSONL
artifacts.

## Shipped artifact: memory control claim gate

The latest scan also repeated a trust concern that shows up whenever coding
agents gain persistent memory: users want useful recall, but they do not want an
agent silently deciding which session fragments become durable project truth.

`akbp client-config` now exposes
`memory_landscape_fit.memory_control_claim_gate`. The gate turns automatic or
self-improving memory-write claims into a reviewed promotion sequence: propose
with `dry_run:true`, show evidence and target artifact paths outside the model
tool call, replay the exact reviewed request with `approved:true` only after
human approval or trusted local policy, then preserve audit output before
another runtime trusts the memory.

If a host can apply background writes without preview, hides citations or
redaction warnings, approves inside an autonomous model-generated tool call, or
drops audit events, AKBP should stay read-only for that host.

## Shipped artifact: compaction survival claim gate

Recent memory-server pitches increasingly claim that project memory survives
conversation compaction, truncation, and session restart. AKBP should make that
claim testable: recovered memory is useful only when it is cited, lifecycle-aware,
bounded, and visible in the adapter's context-use report.

`akbp client-config` now exposes
`memory_landscape_fit.compaction_survival_claim_gate`. The gate requires a
bounded `akbp.session.start` recovery request, preserved citations, lifecycle
freshness, warning and budget fields, adapter context-use reporting, and the
`compaction-handoff-recall` benchmark before an installer claims AKBP memory can
safely guide work after compaction or restart.

If the host can only resume from an uncited compacted chat summary, the safe
fallback is to start fresh or continue without recalled AKBP memory until cited
recovery context can be shown.

## Shipped artifact: context freshness probe example

Recent memory-server and coding-agent setup patterns keep pushing toward shared
persistent context, but the failure mode is still stale context that sounds
authoritative after its source files drift.

`examples/context-freshness-probe/` turns AKBP's freshness contract into a
runnable adapter preflight. It proves the green path with `akbp.source.verify`
and cited `akbp.session.start`, then mutates the source note and verifies that
strict startup context fails closed before stale recalled memory can influence
planning.

Adapters should treat this as the minimum freshness gate for inherited memory,
handoff notes, or startup context from a previous session: verify sources, fetch
bounded cited context, and continue without recalled AKBP memory when either
step fails.

## Shipped artifact: ingest signal references

The latest lightweight scan again showed teams putting coding-agent knowledge
into local markdown folders and then struggling to decide what should become
durable project memory. AKBP should make that promotion reviewable at the line
level, not only as a whole-file import.

`akbp.ingest` now returns `signal_refs` alongside the existing `signals` list in
both dry-run previews and approved apply results. Each signal reference carries
the extracted text, source line, and kind (`heading` or `signal`). This lets an
adapter or review UI point to the exact parts of a long markdown source that
informed the proposed durable claim before a user approves the write.

This keeps the import path aligned with AKBP trust model:

- markdown remains source evidence
- durable claims still require review and approval
- adapters can show line-level provenance before applying memory writes
