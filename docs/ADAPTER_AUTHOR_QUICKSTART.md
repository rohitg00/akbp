# Adapter author quickstart

Use this when adding AKBP support to a coding agent, IDE agent, task runner, or local assistant runtime.

The adapter's job is translation only. It should connect runtime events to AKBP reads and review-gated writes without creating a separate durable memory format.

## 0. Pick the KB scope and trust boundary

Before wiring tools, decide which AKBP folder the runtime may trust. This keeps
adapter behavior predictable when users also have personal assistants, team
profiles, transcript watchers, or migration imports.

| Adapter scenario | Recommended KB scope | First mode | Write rule |
|------------------|----------------------|------------|------------|
| Coding agent in one repo | Repo-local project KB | Read-only startup context | Preview `akbp.session.end`, `akbp.remember`, or `akbp.ingest`; apply only after explicit approval |
| Editor agent across several repos | One KB per repo checkout | Read-only per workspace | Never write to a different repo's KB unless the user selected it |
| Local desktop assistant | Personal KB outside public repos | Read-only | Require a local review surface before any durable preference or workflow write |
| Team automation or CI | Team/project KB | Dry-run by default | Treat CI output as a proposal unless a trusted policy approves the exact request |
| Transcript sidecar or hook | Same repo-local KB as the session | Dry-run session crystallization | Summarize durable claims only; do not ingest raw private transcripts wholesale |
| Migration helper | Temporary staging KB, then reviewed import | Import-check first | Reject unsafe or uncited records before applying to the target KB |

If a runtime cannot tell the user which KB it is reading or writing, keep it
read-only. AKBP's durable value comes from reviewable scope, citations, and
auditability, not from silently accumulating more memory.

When several clients should share memory, point them at the same explicit
knowledge-base path and use `client-config.multi_client_scope` as the contract.
Each client keeps its own scratchpads and private logs outside AKBP, reads
reviewed context from the shared KB, and applies durable writes only through the
same dry-run and approved-apply boundary. Stale shared claims should be
superseded or contradicted, not overwritten by whichever client ran last.

For runtimes that already keep scratchpads, chat summaries, local caches, or
private memory, apply `docs/SESSION_MEMORY_BOUNDARY.md`: keep transient session
state in the runtime, then promote only reviewed durable candidates through
`akbp.session.end` with `dry_run:true` and an approved apply.

Adapter installers that start from an arbitrary workspace directory can run
`akbp discover` first. It walks upward to the nearest `akbp.json`, reports the
resolved KB path, default scope, artifact presence, trust-boundary rules, and
the next `doctor --profile` and `client-config` commands. The discovery payload
also includes `positioning` so installers can show that AKBP is the portable,
reviewable artifact layer beside memory servers, repository instruction files,
tool-protocol hosts, and rebuildable search indexes. It also includes
`first_run_proof`, an ordered checklist for proving read-only setup, cited
startup context, dry-run preview, and the `approval_required` stop signal before
reviewed writes are enabled. If discovery fails,
continue without durable memory instead of creating hidden state.
Discovery also returns `ten_minute_proof` for installer UIs. It turns the
first-run value proposition into structured checks: no Docker, no cloud account,
no secrets, visible AKBP artifacts, cited startup context, dry-run review,
`approval_required` for unapproved applies, adapter response-contract validation,
and export-checkable portability.
Discovery also returns `adapter_prompt_contract`, a compact set of runtime
instructions for the first trusted memory call. Use it when the host needs
pasteable system rules: call `akbp.session.start` before planning from memory,
trust only cited items, continue without recalled memory when context is empty
or uncited, preview writes with `dry_run:true`, apply only the exact reviewed
request with `approved:true`, and branch on `ok` plus `error.code`.

## 1. Generate a read-only client config first

Start with a read-only config when you are evaluating a runtime or wiring a new host. It proves startup retrieval and capability negotiation without granting durable write access.

```bash
python3 cli/akbp.py --path ./my-kb init
python3 cli/akbp.py --path ./my-kb client-config --name my-adapter --profile read-only
```

The generated config includes the server command, knowledge-base path, startup `akbp.capabilities` request, required workflow profile, `akbp.doctor` health check, session-start method, structured response contract, verification expectations, quality gates, and safety rules. Paste that into the host runtime, then run the config's `verification` steps before adding write flows.
The generated config also includes `ten_minute_proof` so setup UIs can show the
smallest verified AKBP value proof instead of vague memory claims: local-first
artifacts, no Docker or cloud requirement, cited startup context, review-gated
writes, structured response-contract validation, and export-checkable
portability.

Use the config's `quality_gates.startup_context` block as the adapter stop condition before planning from recalled memory. A runtime should require cited context items, surface warnings, and continue without recalled memory when startup context is empty or uncited instead of inventing prior decisions.
Use `adapter_prompt_contract.system_rules` as the host-facing memory prompt and
`adapter_prompt_contract.validation` as the response fields the bridge must
preserve. This keeps structured prompts tied to the same JSONL response contract
that the harness verifies.
Use `adapter_prompt_contract.context_use_report` as the host's memory-use audit
shape before planning from recalled context. The host should record whether
AKBP context was used, which context item ids and citation ids supported the
plan, whether warnings were surfaced, and the fallback reason when it continues
without recalled memory. This prevents adapters from compressing cited AKBP
items into an uncited prose summary and then treating that summary as durable
project memory.

For adapter packages, docs, or installer templates that may be committed to a
public repository, generate a placeholder-based config instead of embedding a
machine-local absolute path:

```bash
python3 cli/akbp.py --path ./my-kb client-config --name my-adapter --profile read-only --portable
```

The portable config marks `knowledge_base.portable_template:true` and uses
`<AKBP_KB_PATH>` for every request path. Resolve that placeholder during
install or first run, then run the same verification steps against the local
path.

For installer scripts or setup checks, use the profile-aware doctor preflight:

```bash
python3 cli/akbp.py --path ./my-kb doctor --profile read-only
```

The command returns the normal JSON doctor report and exits non-zero when the requested profile is not ready. This matters because a KB can have valid base files while still missing the index, sources, or reviewed-write readiness an adapter expects.

Hosted or autonomous tool environments should stay on the read-only profile unless there is a separate human approval step outside the tool call. A runtime that can call tools without showing a dry-run preview cannot safely use the reviewed-write profile by itself.

Use reviewed writes only after the runtime can show a preview and collect approval:

```bash
python3 cli/akbp.py --path ./my-kb client-config --name my-adapter --profile reviewed-writes
```

That profile still requires review-gated writes. The adapter must surface `dry_run:true` previews, warnings, would-write paths, and the `apply_instruction`, then repeat the same method/path/params with `approved:true` after approval.

### Adapter path matrix

Use this matrix to choose the first integration path. Start read-only unless the
host can show previews and collect approval before any durable write.

| Runtime type | Transport | Starter artifact | Session start | Write path | Approval requirement |
|--------------|-----------|------------------|---------------|------------|----------------------|
| Terminal coding agent | stdio JSONL or CLI | `akbp client-config --profile read-only` | `akbp.session.start` | `akbp.remember`, `akbp.ingest`, or `akbp.session.end` | Use reviewed writes only when the terminal flow shows `dry_run:true` output and waits for explicit approval. |
| Editor or IDE agent | stdio JSONL | `adapters/editor-coding-agent/` or `adapters/coding-agent-template/` | Runtime startup hook calls `akbp.session.start` | Editor command previews write-capable calls | The UI must render warnings, redaction status, would-write paths, and the apply instruction before retrying with `approved:true`. |
| Local assistant or desktop runtime | stdio JSONL behind local config | `akbp client-config --profile read-only` | Assistant session open calls `akbp.session.start` | Keep read-only unless the assistant has a trusted local approval surface | Autonomous background writes should stay disabled; approval must happen outside the model-generated tool call. |
| Custom script or task runner | CLI or stdio JSONL | `examples/stdio-client-config/` | Script calls `akbp.context` or `akbp.session.start` before work | Script previews import, ingest, remember, or session-end requests | CI and scheduled jobs should use `dry_run:true` by default and require a human or trusted policy before `approved:true`. |
| Hosted or remote tool bridge | Remote wrapper around local AKBP | Local read-only config plus wrapper docs | Wrapper exposes read-only retrieval first | Avoid durable writes until the remote trust boundary is documented | Do not treat remote tool execution as user approval; keep writes blocked unless a separate review channel exists. |
| Tool-protocol host bridge | Host tools forwarding to the local JSONL server | `docs/TOOL_PROTOCOL_BRIDGE.md` | Bridge calls `akbp.capabilities`, `akbp.doctor`, then exposes read-only context tools | Keep direct write tools disabled; expose dry-run previews only after review UI exists | The apply call must repeat the exact reviewed method/path/params with `approved:true`; a tool call is not approval. |

## 2. Start from the template

Copy the runtime-neutral template:

```bash
cp -R adapters/coding-agent-template adapters/<runtime-name>
```

Required files:

```text
README.md
instructions.md
config.example.json
session-start.md
session-end.md
privacy.md
```

Keep examples public-safe. Do not include local usernames, private paths, tokens, cookies, auth headers, screenshots, private chat text, or production logs.

## 3. Discover capabilities before calling methods

An adapter should call `akbp.capabilities` at startup and cache the response for the session. Adapter config examples expose a `lifecycle` block that maps runtime hooks to `akbp.session.start` and `akbp.session.end`; keep that mapping explicit so users can audit what writes may happen at shutdown.

JSONL request:

```json
{"id":"caps-1","method":"akbp.capabilities","params":{"client":"example-adapter","requires":["method_param_schemas","capability_negotiation","write_apply_requires_approval"],"requires_profiles":["read_only","startup_context"]}}
```

The response includes `result.negotiation.satisfied`. If it is `false`, disable or degrade the flows named in `unsupported_features` or `unsupported_profiles` instead of guessing.
It also includes `result.profile_contracts`, a machine-readable map from workflow profiles to their purpose, risk level, write policy, review-surface requirement, and matching doctor readiness field. Use that map in installers and setup screens so users can see why a host starts read-only and what must change before reviewed writes are enabled.
It also includes `result.knowledge_capability.retrieval.scope_policy`, which is
the adapter rule for workflow-aware context: pass the explicit KB `path` plus a
bounded `params.task` or `params.query` when calling `akbp.session.start` or
`akbp.context`. If the host cannot tell which repo, workspace, workflow, or user
task the memory belongs to, keep running without recalled context instead of
mixing unrelated memory into the prompt.

Generated client configs also include `response_contract.error_actions`. Use that
map as the adapter's failure policy before writing host-specific glue:
`invalid_json` and `invalid_request` are client bugs, `unknown_method` requires
a capability refresh, `invalid_params` requires payload repair from the
advertised schema, `approval_required` is a hard stop until reviewed approval,
and `cli_error` or `internal_error` must not be treated as successful writes.

Adapter checks:

- method exists before use
- method parameter schema is advertised when validation is needed
- write policy is understood
- `dry_run` support is present for write-capable flows
- approval field is known before applying writes

Do not hard-code future methods. If a method is missing, degrade gracefully and tell the user which capability is unavailable.

Minimum startup gate:

1. Call `akbp.capabilities`.
2. Confirm `result.negotiation.satisfied` is `true` for required features.
3. Confirm required workflow profiles such as `read_only` or `startup_context` are present in `result.negotiation.supported_profiles`.
4. Read `result.profile_contracts[profile].ready_field` for the requested profile and use that field as the bridge between capability discovery and `akbp.doctor`.
5. Call `akbp.doctor` and show `next_steps` if `ready_for_adapter` is `false`; use `adapter_readiness.recommended_profile` to decide whether the host should stay in setup-only, read-only, or reviewed-write mode.
6. Read `security_posture` from the doctor report and keep writes disabled unless `write_boundary` is `dry_run_preview_then_approved_apply`, the approval field is `approved`, and the host can follow the listed adapter rules.
7. Confirm `result.features.method_schema_runtime_parity` is `true`.
8. Confirm `result.runtime.method_schema_runtime_errors` is empty.
9. Confirm the write method you plan to call advertises `review_required:true`.

If any check fails, leave read-only mode enabled and explain the missing capability instead of attempting writes.
If `akbp.doctor` returns `adapter_readiness.reviewed_write_ready:false`, keep write flows disabled even when capability negotiation succeeded. Capability discovery tells you what the server supports; doctor tells you whether this specific knowledge base is ready to trust.

For a runnable startup harness, use:

```bash
examples/session-start-harness/run.sh
```

It validates `akbp.capabilities`, `akbp.doctor`, and `akbp.session.start` together so adapter authors can test the first trusted context call before enabling write-capable flows.

For the shortest complete JSONL sequence, use:

```bash
examples/jsonl-quickstart/run.sh
```

It verifies capability discovery, cited startup context, `dry_run:true` write
preview, `approval_required` rejection, `approved:true` apply, approved
index refresh, cited recall, and portable export in one script.

When the runtime also has a shutdown hook, run the lifecycle example next:

```bash
examples/adapter-lifecycle/run.sh
```

It verifies the complete adapter loop: capability negotiation, startup context, `akbp.session.end` dry-run preview, unapproved write rejection, approved apply, index refresh, and recalled context after the write.

Before an adapter treats AKBP output as trusted memory, run the structured output
harness:

```bash
examples/structured-output-harness/run.sh
```

Use it as the response-contract gate for capability discovery, doctor
readiness, cited startup context, dry-run review metadata, and the
`approval_required` stop signal. This is especially useful when a runtime uses
structured prompts internally: the prompt can request fields, but the harness
proves the JSONL server actually returned the schema-backed fields the adapter
will branch on.

Treat these examples as the adapter output quality harness, not just smoke
tests. A structured prompt can ask an agent to return citations, review
metadata, or write decisions, but the harness proves the runtime actually
received schema-backed JSONL responses with the fields the adapter depends on.
For a new adapter, wire the runtime so it blocks planning when startup context
is empty or uncited, blocks writes when `akbp.doctor` recommends read-only mode,
and blocks apply flows unless the dry-run preview contains the expected
`review_required`, `apply_instruction`, and write summary fields. Add a
benchmark fixture with `expected_result_schema`, `expected_result_fields`, and
`expected_error_code` for every response shape the adapter treats as trusted.
The generated `adapter_prompt_contract.source_provenance_gate` is the write-side
check: do not preview a durable claim unless it is backed by an existing source
id, a cited context item, `akbp.cite` evidence, or source material registered
with `akbp.source.add`. Unsupported chat memory stays runtime scratch.

## 4. Retrieve context at session start

Use `akbp.session.start` as the adapter-level session entrypoint. It wraps context retrieval and returns a stable `session_id` plus the normal context pack. Use `akbp.context` and `akbp.search` directly when the runtime needs lower-level calls.

```json
{"id":"session-start-1","method":"akbp.session.start","path":".","params":{"task":"current task goals and constraints","limit":5,"max_chars":4000,"min_items":1,"require_citations":true}}
```

Lower-level context request:

```json
{"id":"ctx-1","method":"akbp.context","path":".","params":{"task":"current task goals and constraints","limit":5,"max_chars":4000,"min_items":1,"require_citations":true}}
```

```json
{"id":"search-1","method":"akbp.search","path":".","params":{"query":"release checklist","limit":5}}
```

The adapter should show citations or source ids when prior knowledge affects a plan or answer.

## 5. Preview writes before applying

All write-capable calls must start as previews.

Example session-end preview:

```json
{"id":"session-end-preview-1","method":"akbp.session.end","path":".","dry_run":true,"params":{"transcript":"session.md","apply":true}}
```

If the response includes review metadata, surface it in the runtime UI or command output:

- `review_required`
- `apply_instruction`
- accepted/rejected object counts
- source/evidence warnings, including changed or missing cited source hashes during retrieval

Apply only after approval or an explicit trusted local policy:

```json
{"id":"session-end-apply-1","method":"akbp.session.end","path":".","approved":true,"params":{"transcript":"session.md","apply":true}}
```

Adapter write state machine:

```text
read-only startup
  -> dry-run preview request
  -> render preview, warnings, would-write paths, and apply_instruction
  -> wait for user approval or trusted local policy
  -> repeat the same method/path/params with approved:true and without dry_run
  -> run akbp.index with approved:true when retrieval state should refresh
  -> fetch context/search again before relying on the new memory
```

Safety rules:

- Never send both `dry_run:true` and `approved:true` in the same request.
- Do not silently alter `params` between preview and apply.
- Do not auto-apply `akbp.session.end` just because a session is closing.
- Do not promote uncited runtime memory, cache entries, or model summaries into
  AKBP claims. Register source material first or keep the observation outside
  durable AKBP artifacts.
- Treat `approval_required` as a stop signal, not a warning.
- Show redacted CLI output as redacted; do not retry with raw secrets.

## 6. Preserve evidence and auditability

When importing source material, prefer source registration plus ingest preview.
Both operations are write-capable, so preview them before applying:

```json
{"id":"source-preview-1","method":"akbp.source.add","path":".","dry_run":true,"params":{"locator":"notes/session.md","type":"file","title":"Session notes"}}
```

```json
{"id":"source-apply-1","method":"akbp.source.add","path":".","approved":true,"params":{"locator":"notes/session.md","type":"file","title":"Session notes"}}
```

```json
{"id":"ingest-preview-1","method":"akbp.ingest","path":".","dry_run":true,"params":{"file":"notes/session.md"}}
```

```json
{"id":"ingest-apply-1","method":"akbp.ingest","path":".","approved":true,"params":{"file":"notes/session.md"}}
```

Verify local file evidence before depending on it:

```json
{"id":"verify-1","method":"akbp.source.verify","path":".","params":{"source_id":"source_..."}}
```

Never convert secrets or raw private logs into durable AKBP records.

## 7. Handle structured errors

Branch on `error.code`, not free-form messages.

Common codes an adapter should handle:

- `approval_required`: show the preview and ask for approval before retrying with `approved:true`.
- `unknown_method`: refresh capabilities and disable that flow.
- `invalid_params`: show the schema-backed parameter issue.
- `cli_error`: show the command failure from the redacted message/stdout, and use `redacted` to explain that sensitive-looking values were hidden.

See `examples/tool-error-handling/README.md`.

## 8. Validate the adapter before publishing

Run:

```bash
make validate
```

Then review:

- `docs/ADAPTER_REVIEW_CHECKLIST.md`
- `docs/AGENT_FLOW.md`
- `docs/TOOL_CONTRACT.md`
- `examples/tool-server-approval-flow/README.md`

## Publication bar

An adapter is publishable when:

- it uses `akbp.capabilities` before method assumptions
- startup retrieves cited context
- writes are dry-run first and approval-gated
- session-end memory uses `akbp.session.end` or `akbp.crystallize_session` where possible
- private data and secrets are excluded by default
- examples are copy-pasteable and public-safe
- `make validate` passes
