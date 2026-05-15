# Cross-Runtime Context Handoff

Different coding agents now keep project context in different places: repository
instructions, editor rules, chat summaries, local memory servers, tool-protocol resources,
and tool-specific profile folders. That is useful inside one runtime, but it is
fragile when a project moves between Claude Code, Codex, Cursor, Gemini CLI,
OpenClaw, hosted agents, and local assistants.

AKBP's job in that flow is not to replace every runtime's context mechanism. It
is to give them one reviewed, file-backed knowledge substrate they can all read
from and write to safely.

## Recent signal

The current agent-memory discussion is converging on three practical gaps:

- users want one project memory that survives tool switches rather than a
  separate private memory per agent
- tool protocols and local tool servers are becoming the common way to expose context and
  actions to many clients
- teams are worried about silent memory writes, stale summaries, and private
  data leaking into shared project state

That makes cross-runtime handoff a first-class AKBP use case: each runtime can
keep its own prompt, rules, and UI, while durable project knowledge remains
portable, cited, reviewable, and auditable.

## Handoff contract

Use this contract when moving work from one agent runtime to another.

| Step | Runtime obligation | AKBP operation |
|------|--------------------|----------------|
| Discover | Detect whether the project has an AKBP knowledge base and call capabilities before assuming methods | `akbp.capabilities` |
| Read | Retrieve only task-scoped context, with citations, before planning substantial work | `akbp.session.start` or `akbp.context` |
| Work | Keep transient reasoning, scratch notes, and tool-specific logs inside the runtime | no durable write |
| Propose | Convert only durable facts, decisions, constraints, and evidence-backed findings into preview records | `akbp.session.end`, `akbp.remember`, `akbp.ingest`, or `akbp.crystallize_session` with `dry_run:true` |
| Review | Show the preview, warnings, source IDs, skipped records, and apply instruction to the user or trusted local policy | response `result.review_required` and `result.apply_instruction` |
| Apply | Write durable memory only after explicit approval | repeat the same request with `approved:true` |
| Refresh | Rebuild local retrieval state after approved writes | `akbp.index` |
| Handoff | The next runtime starts from AKBP context, not from a copied chat transcript | `akbp.session.start` |

## What belongs in AKBP

Store durable project knowledge that should survive a tool switch:

- architecture decisions
- release rules
- recurring setup constraints
- incident learnings
- validated benchmark results
- source-backed user preferences for the project
- supersession or contradiction links when old knowledge changes

Keep these out of AKBP unless they have been deliberately reviewed:

- private DMs, credentials, tokens, cookies, and auth headers
- raw chat transcripts copied wholesale
- scratch reasoning or unverified guesses
- runtime-specific cache files
- personal memory that does not belong in the project trust boundary

## Adapter behavior

Every adapter should make the handoff boundary explicit:

1. Read AKBP context before planning, but keep it compact and cited.
2. Prefer read-only mode until the runtime can show write previews clearly.
3. Treat `dry_run:true` as the default for all memory writes.
4. Never convert an entire transcript into durable memory automatically.
5. Apply writes only with request-level `approved:true`.
6. Store the durable result in AKBP markdown and JSONL artifacts, not in a
   runtime-only memory folder.
7. Use lifecycle methods to supersede stale knowledge instead of deleting or
   overwriting it silently.

## Minimal JSONL flow

```json
{"id":"caps","method":"akbp.capabilities"}
{"id":"start","method":"akbp.session.start","path":".","params":{"task":"continue release work","limit":5}}
{"id":"preview","method":"akbp.session.end","path":".","dry_run":true,"params":{"summary":"Decision: release notes must cite validation output.","type":"decision"}}
{"id":"apply","method":"akbp.session.end","path":".","approved":true,"params":{"summary":"Decision: release notes must cite validation output.","type":"decision"}}
{"id":"index","method":"akbp.index","path":".","approved":true,"params":{"incremental":true}}
```

If a hosted or autonomous runtime cannot display the preview and collect
explicit approval, keep it on the `read_only` profile and send memory proposals
to a local review step instead.

## Acceptance checks

A cross-runtime adapter is ready only when it can prove:

- startup context includes citations
- write-capable methods are blocked or previewed by default
- unapproved writes return `approval_required`
- approved writes land in portable AKBP artifacts
- later sessions can retrieve the approved knowledge from a different runtime
- export-check passes after the handoff flow

Use this document with `docs/ADAPTERS.md`, `docs/AGENT_FLOW.md`,
`docs/ADAPTER_AUTHOR_QUICKSTART.md`, and `examples/adapter-lifecycle/`.
