# Stdio client config

This example shows how an adapter author can generate a pasteable AKBP stdio JSONL configuration before writing any runtime glue.

The generated config makes the trust boundary visible:

- call `akbp.capabilities` before assuming methods or schemas
- run `akbp.doctor` before trusting startup retrieval or write flows
- request either `read_only` or `reviewed_write`
- expose local-first install requirements, including no network, cloud account,
  or secrets required for the reference stdio flow
- expose a multi-client scope contract so several runtimes can share one
  selected KB while keeping private scratchpads and caches outside AKBP
- expose `scope_selection` so installers make the first-run trust question
  explicit before creating or reusing durable memory
- expose `adapter_prompt_contract.source_provenance_gate` so adapters reject
  uncited runtime memory before previewing durable AKBP writes
- expose a first-run sequence that orders path resolution, capability negotiation, doctor readiness, cited startup context, and reviewed-write gating
- include request ids and the knowledge-base path in startup checks
- include a structured response contract so adapters branch on `ok` and `error.code`
- include a structured error-action map so bridge installers can recover from
  `invalid_json`, `invalid_request`, `unknown_method`, `invalid_params`,
  `approval_required`, `cli_error`, and `internal_error` without parsing prose
- include a verification plan with expected pass fields for startup, doctor, and session-start calls
- include a tool-protocol bridge allowlist and blocked write methods
- include a managed tool-host bridge contract for stdio-compatible hosts
  without turning AKBP into an opaque memory store
- include `memory_server_bridge.external_memory_promotion`, a concrete
  source-backed candidate-record contract for promoting existing memory-server
  rows through import-check, dry-run preview, and approved apply
- include a hosted-agent policy for managed coding agents that cannot run the
  local stdio server beside AKBP artifacts or cannot show reviewed write
  previews
- include tool-protocol bridge snippets that are explicit about requiring a
  bridge rather than claiming the JSONL reference server is a direct host-native
  tool server
- include manifest-level `preflight_requests` that adapters can execute before exposing host tools
- retrieve context with `akbp.session.start`
- keep durable writes blocked unless the adapter implements dry-run review and `approved:true`
- keep hosted or autonomous tool integrations read-only unless a separate human approval step exists outside the tool call
- emit a `--portable` template with `<AKBP_KB_PATH>` so adapter examples can be committed without leaking machine-local paths

## Run

From the repository root:

```bash
examples/stdio-client-config/run.sh
```

Expected success marker:

```text
AKBP stdio client config example passed
```

## What it proves

- `akbp client-config` emits valid JSON for both read-only and reviewed-write adapters
- `akbp client-config --portable` emits a commit-safe template that installers can resolve at first run
- the config exposes `first_run_sequence` so adapter installers have one ordered checklist with explicit stop conditions before trusting recalled memory
- the config exposes `runtime_requirements` so adapter installers can show the
  local-first/no-cloud/no-secret setup boundary before asking for trust
- the config exposes `harness_adoption_fit` so adapter installers can turn
  structured-output and harness expectations into a machine-checkable setup
  gate before trusting recalled memory or enabling write tools
- the config exposes `multi_client_scope` so adapter installers can wire
  multiple clients to one reviewed KB without hidden per-client memory stores
- the config exposes `scope_selection` so adapter installers can distinguish
  repo-local, team-shared, personal-assistant, and migration KB boundaries
  before enabling recalled context
- the config exposes `knowledge_capability` so host registries can label AKBP
  as durable, cited, review-gated agent knowledge instead of opaque memory
- the config starts with capability negotiation instead of hard-coded assumptions
- the config exposes a health check that adapters can map to setup warnings and next steps
- the config exposes the response envelope and schema paths adapter authors should validate against
- the config exposes `response_contract.error_actions` so adapters can map each
  structured failure to a retry and write-safety policy
- the config exposes `adapter_prompt_contract.source_provenance_gate` so
  durable claims require source ids, cited context evidence, or newly registered
  source material before the dry-run preview
- the config exposes `tool_protocol_bridge` so tool-protocol hosts can start with read-only allowlists
- the config exposes `managed_tool_host_bridge` so tool-protocol-compatible hosts can launch the
  same local stdio server, run preflight requests, preserve structured
  responses, and keep writes blocked until reviewed-write readiness and a
  separate approval surface exist
- the config exposes `memory_server_bridge.external_memory_promotion` so
  existing memory servers can stage source-backed candidate records and reject
  missing-source, secret-like, private-chat, cache-only, stale-source, or
  unapproved rows before durable AKBP writes
- host install profiles include managed tool-protocol hosts where read-only startup context is safe but durable writes stay disabled until a separate approval UI exists
- hosted-agent policy keeps managed cloud or remote tool hosts read-only unless
  a user-controlled bridge preserves AKBP envelopes, citations, warnings, and
  dry-run review metadata
- host-tool manifests include descriptions and safety metadata for each generated read-only wrapper
- tool-protocol-capable hosts get copyable bridge inputs while the safe default
  stays read-only and write apply remains blocked without a separate review
  surface
- host-tool and client-tool manifests include executable preflight requests for capability negotiation, doctor, and bounded startup context
- the config tells adapter authors which calls to run and which result fields must pass before trusting setup
- reviewed-write configs keep the dry-run and approval boundary explicit
- configs describe the host trust boundary so adapter authors do not accidentally treat autonomous tool execution as reviewed writes
