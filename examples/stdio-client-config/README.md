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
- expose a first-run sequence that orders path resolution, capability negotiation, doctor readiness, cited startup context, and reviewed-write gating
- include request ids and the knowledge-base path in startup checks
- include a structured response contract so adapters branch on `ok` and `error.code`
- include a structured error-action map so bridge installers can recover from
  `invalid_json`, `invalid_request`, `unknown_method`, `invalid_params`,
  `approval_required`, `cli_error`, and `internal_error` without parsing prose
- include a verification plan with expected pass fields for startup, doctor, and session-start calls
- include a tool-protocol bridge allowlist and blocked write methods
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
- the config exposes `tool_protocol_bridge` so tool-protocol hosts can start with read-only allowlists
- host-tool manifests include descriptions and safety metadata for each generated read-only wrapper
- host-tool and client-tool manifests include executable preflight requests for capability negotiation, doctor, and bounded startup context
- the config tells adapter authors which calls to run and which result fields must pass before trusting setup
- reviewed-write configs keep the dry-run and approval boundary explicit
- configs describe the host trust boundary so adapter authors do not accidentally treat autonomous tool execution as reviewed writes
