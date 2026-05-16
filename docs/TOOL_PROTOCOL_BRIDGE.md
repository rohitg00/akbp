# Tool-Protocol Bridge Guide

Use this guide when a tool-protocol host wants AKBP context without turning AKBP into an opaque memory server.

Recent local memory tools are converging on tool-call bridges because they are a convenient way to expose context to coding agents and desktop assistants. AKBP can sit behind a bridge, but the bridge should preserve the AKBP trust model: local artifacts are the source of truth, startup context is cited, and durable writes are previewed before approval.

## Recommended first bridge

Start with a read-only bridge that forwards a small allowlist to the local JSONL server:

Use `akbp discover` first when an installer or host setup flow has not yet
chosen a bridge profile. The `tool_protocol_bridge_preflight` section gives the
safe default, the next `client-config` command, read-only methods, blocked
direct-write methods, fields the host must preserve, and the runnable
`examples/tool-protocol-bridge/run.sh` preflight. Treat that as the decision
point before generating a full host manifest.

Use `akbp client-config --profile read-only` as the machine-readable starting point for an adapter installer. The generated `tool_protocol_bridge` section includes the read-only allowlist, blocked write methods, reviewed-write wrapper names, and the apply rule for repeating the exact reviewed method, path, and params.

It also includes `tool_protocol_bridge.forward_tools`: a ready wrapper map for tool-protocol hosts. Each entry gives the host-facing tool name, AKBP JSONL method, method-parameter schema reference, and response fields the bridge should preserve in its own response. Use that map when generating tool-protocol tools, IDE commands, or local assistant actions instead of inventing a second memory contract.

The same config includes `knowledge_capability` for installers and host
registries that need to label what AKBP provides. Treat it as
`durable_agent_knowledge`: local-first, cited, bounded, review-gated, and
export-checkable. Do not advertise it as a chat transcript store, runtime
scratchpad, uncited vector cache, bridge-owned memory format, or automatic
background write sink.

For hosts that maintain their own capability registry, use
`host_capability_descriptor` from `akbp client-config`. It is a compact,
machine-readable profile map for tool-protocol clients and other tool hosts:
`startup_context` and `read_only` are safe without a review surface, while
`reviewed_write` requires visible dry-run previews and an `approved:true`
apply of the exact reviewed request. This descriptor is intentionally about the
knowledge capability and trust boundary, not a claim that AKBP is a separate
host protocol.

When a host only has a generic memory-capability slot, use
`memory_capability_projection` from `akbp client-config`. It gives the host a
minimal mapping: AKBP is durable project knowledge, `akbp.session.start` is the
startup read, read-only methods are the safe default, direct writes are disabled,
and write-capable methods stay behind `dry_run` preview plus exact
`approved:true` replay. If the host memory slot cannot represent citations,
structured `error.code`, context budgets, or reviewed-write metadata, register
only read-only startup-context tools.

The generated `tool_protocol_bridge.host_tool_manifest` is the smallest
host-facing manifest for the selected profile. For `startup_context`, it only
publishes capability discovery, doctor, session start, and bounded context. For
`read_only` and `reviewed_write`, it publishes the broader read-only inspection
surface while keeping write-capable methods blocked. The manifest repeats the
stdio command, local knowledge-base path, tool names, AKBP method targets,
parameter schema refs, and response fields the bridge must preserve. Generate
host tools from that manifest when possible; do not copy the list into a
separate memory server config that can drift from `akbp.capabilities`.

The same payload includes `tool_schema_budget`. Treat
`budget_check:"pass"` as the gate before exposing generated host tools. If
`exposed_method_count` is greater than `max_exposed_methods_for_profile`, or
`within_budget` is false, keep only the startup-context tools and rerun
`client-config` for the intended profile.
Use `tool_schema_budget.schema_exposure_plan.publish_now` as the exact list of
method schema refs the host may publish for the selected profile. Keep schemas
listed under `defer_until_review_surface` out of the host prompt and direct tool
manifest until dry-run review, explicit approval, and exact `approved:true`
apply are preserved. This keeps schema budget claims testable instead of relying
on prose instructions.

The same manifest includes `preflight_requests` for the startup checks an
adapter should run before exposing tools: capability negotiation, doctor, and
bounded startup context. Use these generated JSONL requests as the executable
harness contract instead of reconstructing preflight calls from prose.
It also includes `preflight_replay.request_jsonl`, a copyable newline-delimited
request block for smoke-testing the local JSONL server before a host publishes
tools. Treat any failed replay, missing citations, unsurfaced warnings, or
lost `error.code` as a bridge failure and keep AKBP read-only.

For managed tool-protocol hosts, use the generated `managed_tool_host_bridge` section instead
of hand-writing a separate memory-server contract. It reuses the same local
stdio command, knowledge-base path, read-only wrapper list, blocked write
methods, and preflight requests while making the fallback explicit: if the
host cannot preserve citations, warnings, structured errors, and dry-run
review metadata, expose AKBP as read-only startup context only.

For hosted coding agents or managed tool hosts that cannot run the local stdio
server beside AKBP artifacts, also read the generated `hosted_agent_policy`.
The safe default is read-only. Write-capable flows stay disabled unless the
host reaches a user-controlled bridge that preserves AKBP envelopes, citations,
warnings, budget fields, and review metadata, and applies durable writes only
from a local checkout or CI step with visible approval.

For a runnable preflight, use `examples/tool-protocol-bridge/run.sh`. It checks
that the generated wrapper map stays read-only, that blocked write methods are
not exposed as direct bridge tools, that startup context returns cited items,
and that a direct unapproved write returns `approval_required`.

| Bridge tool | Forward to AKBP | Why expose it first |
| --- | --- | --- |
| `akbp_capabilities` | `akbp.capabilities` | Discover profiles, method schemas, and write policy before assuming behavior |
| `akbp_doctor` | `akbp.doctor` | Show whether this knowledge base is ready for adapter use |
| `akbp_session_start` | `akbp.session.start` | Return compact cited startup context for the current task |
| `akbp_context` | `akbp.context` | Retrieve bounded cited context during a session |
| `akbp_search` | `akbp.search` | Search reviewed local artifacts without granting write access |
| `akbp_cite` | `akbp.cite` | Inspect evidence before relying on a claim |
| `akbp_source_verify` | `akbp.source.verify` | Check source drift before trusting old evidence |
| `akbp_import_check` | `akbp.import_check` | Validate a bundle without applying records |

Do not expose write-capable methods in the first bridge unless the host has a separate review surface. If the host cannot show a dry-run preview and wait for explicit user approval, keep the bridge read-only.

## Evaluate memory-server bridges

When comparing AKBP with a memory server, plugin, or tool-protocol bridge, do
not stop at transport setup. A bridge is useful only if it preserves the
knowledge contract that makes later agent sessions trustworthy.

Use this adoption checklist before enabling a bridge:

| Check | AKBP requirement | Why it matters |
| --- | --- | --- |
| Artifact ownership | Durable knowledge remains in AKBP files, not bridge-owned state | Users can inspect, version, export, and migrate memory without the bridge |
| Capability freshness | The bridge starts from `akbp.capabilities` and generated `client-config` data | Host tools do not drift from supported methods, schemas, profiles, or write policy |
| Cited startup context | The first planning context comes from `akbp.session.start` or `akbp.context` with citations | Agents can show where recalled knowledge came from before acting |
| Write boundary | Direct write methods stay blocked until dry-run preview and approval UI exist | Tool execution is not silently treated as user approval |
| Error handling | The bridge preserves `ok`, `error.code`, warnings, and budget fields | Hosts can branch on `approval_required`, `invalid_params`, and source drift |
| Portability | Export and import checks still work without bridge-local metadata | Knowledge can move across runtimes instead of being trapped in one server |

For hosts that already have a memory server, read
`memory_server_bridge.promotion_contract` from `akbp client-config`. It gives a
machine-readable promotion rule: only durable project decisions, source-backed
facts, workflow constraints, and lifecycle records should move into AKBP; runtime
scratchpads, uncited summaries, private logs, secret-like values, and bridge-only
cache metadata should stay out. The bridge should run capability and doctor
preflights, then use `akbp.import_check` or a dry-run `akbp.remember` preview
before applying the exact reviewed record with `approved:true`.
The promotion contract also includes `intake_classification`, a triage table for
external-memory rows: `runtime_scratch` stays outside AKBP, `ephemeral_hint`
can help find source material, `candidate_durable_claim` may go through
`import-check` and dry-run preview, and `blocked_private_or_secret` is rejected
without echoing private or secret-like data into durable memory.

For hosts that also advertise product-native memory or external memory tools, read
`native_memory_interop` from `akbp client-config`. It makes the first-run policy
explicit: retrieve cited AKBP startup context before planning, treat native
memory as ephemeral hints until citations confirm a durable project fact, and
resolve conflicts through reviewed `supersede` or `contradict` records instead
of silently letting two memory systems disagree.

If a bridge only stores memories behind a tool call and cannot show citations,
artifact paths, dry-run review metadata, or export-checkable bundles, treat it
as an integration experiment rather than a durable AKBP memory path.

## Bridge contract

The bridge is translation glue only. It should not create another durable memory format.

Required behavior:

- Call `akbp.capabilities` at startup and require `read_only` plus `startup_context` for the first bridge.
- Preserve `knowledge_capability.type`, `guarantees`, and `not_a` when the host has its own capability registry or marketplace metadata.
- Preserve `host_capability_descriptor.profile_contracts` when the host has
  first-class capability records, so write-capable flows stay disabled until a
  review surface exists.
- Preserve `host_capability_descriptor.tool_protocol_memory_capability` when a
  host wants to label AKBP as a memory capability. Register it only as cited,
  review-gated project knowledge; if the host cannot express citations,
  structured errors, context budgets, or reviewed writes, expose read-only
  startup context tools instead of a generic memory store.
- Preserve `memory_capability_projection` when the host has a generic memory
  registry. Treat its `read_methods`, `startup_method`, `write_boundary`,
  and `host_must_preserve` fields as the host mapping contract.
- Generate read-only host wrappers from `tool_protocol_bridge.forward_tools` when available, preserving each entry's `method`, `params_schema`, and `surface_fields`.
- For managed tool-protocol hosts, generate the local server entry and read-only tool
  exposure from `managed_tool_host_bridge` so the host config cannot drift from AKBP
  capabilities, preflight requests, and write blocking policy.
- For hosted agents, apply `hosted_agent_policy`: expose only the hosted
  allowlist unless there is a user-controlled bridge and visible reviewed-write
  approval path.
- Run `tool_protocol_bridge.host_tool_manifest.preflight_requests` before exposing host tools, and branch on the structured `expect` fields.
- Use `tool_protocol_bridge.preflight_replay.request_jsonl` as the runnable
  smoke test when the host needs a pasteable setup check instead of a manifest parser.
- Check `tool_schema_budget.within_budget` before publishing host tools; do
  not flatten every AKBP method schema into the model prompt by default.
- Publish only the method schemas listed in
  `tool_schema_budget.schema_exposure_plan.publish_now`; deferred schemas stay
  disabled until the reviewed-write trust gate passes.
- Use the generated `maintenance` checks to verify sources, rerun `akbp.doctor`, check export bundles, and refresh retrieval after approved writes instead of treating setup as a one-time install.
- Pass a caller-selected local knowledge-base path instead of hard-coding a private machine path.
- Enforce bounded requests before forwarding to the JSONL server.
- Return AKBP response envelopes or preserve `ok`, `result`, and `error.code` in the host response.
- Use `response_contract.error_actions` from `akbp client-config` as the bridge
  failure policy so unsupported methods, invalid params, approval stops, CLI
  failures, and internal failures do not collapse into generic text errors.
- Surface citations, source ids, warnings, and `budget` fields when returning context.
- Treat `approval_required` as a stop signal, not a warning.
- Redact secret-like values in logs and never store raw tool requests as durable memory.
- Keep `.akbp/` runtime state local and export only portable markdown and JSONL artifacts.

## Reviewed-write bridge

Only add write-capable tools after the host can display review metadata and collect approval outside the model-generated tool call.

| Bridge tool | Forward to AKBP | Required bridge behavior |
| --- | --- | --- |
| `akbp_remember_preview` | `akbp.remember` with `dry_run:true` | Show `review_required`, `apply_instruction`, warnings, and would-write paths |
| `akbp_session_end_preview` | `akbp.session.end` with `dry_run:true` | Preview transcript crystallization without writing durable claims |
| `akbp_ingest_preview` | `akbp.ingest` with `dry_run:true` | Preview claims from a cited file |
| `akbp_apply_reviewed` | same method/path/params with `approved:true` | Apply only the exact reviewed request |
| `akbp_index_apply` | `akbp.index` with `approved:true` | Refresh retrieval after approved writes |

The apply call must repeat the reviewed method, path, and params. Do not silently rewrite the claim text, evidence, entity list, source locator, or transcript path between preview and apply.

## Minimal request flow

```text
Tool host starts
  -> bridge calls akbp.capabilities with requires_profiles ["read_only", "startup_context"]
  -> bridge calls akbp.doctor
  -> bridge exposes read-only tools only if the knowledge base is adapter-ready
  -> agent calls akbp_session_start before planning
  -> user sees cited context
```

Reviewed writes add one more explicit gate:

```text
agent proposes durable memory
  -> bridge forwards dry_run:true
  -> host renders review_required, apply_instruction, warnings, and would-write paths
  -> user or trusted local policy approves the exact request
  -> bridge forwards approved:true
  -> bridge refreshes the index when retrieval should include the new record
```

## Failure modes to avoid

- Exposing `akbp.remember`, `akbp.ingest`, `akbp.import_apply`, or `akbp.session.end` as direct one-step bridge tools.
- Treating a tool call as user approval.
- Returning uncited summaries when AKBP returned cited context items.
- Copying chat transcripts or private logs into AKBP without source review.
- Storing durable memory in the bridge instead of AKBP artifacts.
- Hiding `error.code` behind free-form text so the host cannot branch on `approval_required` or `invalid_params`.

## Validation

Before publishing a bridge:

```bash
make guard
make test
make smoke
make install-smoke
```

Then manually verify:

1. A read-only bridge can retrieve `akbp.session.start` context with citations.
2. A write attempt without approval returns `approval_required`.
3. A dry-run preview returns review metadata without durable writes.
4. An approved apply only writes the exact reviewed request.
5. Export and import checks still work without bridge-owned state.

For general adapter behavior, read `docs/ADAPTER_AUTHOR_QUICKSTART.md` and `docs/TOOL_CONTRACT.md`.
