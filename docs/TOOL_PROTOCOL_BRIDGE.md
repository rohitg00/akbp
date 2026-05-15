# Tool-Protocol Bridge Guide

Use this guide when a tool-protocol host wants AKBP context without turning AKBP into an opaque memory server.

Recent local memory tools are converging on tool-call bridges because they are a convenient way to expose context to coding agents and desktop assistants. AKBP can sit behind a bridge, but the bridge should preserve the AKBP trust model: local artifacts are the source of truth, startup context is cited, and durable writes are previewed before approval.

## Recommended first bridge

Start with a read-only bridge that forwards a small allowlist to the local JSONL server:

Use `akbp client-config --profile read-only` as the machine-readable starting point for an adapter installer. The generated `tool_protocol_bridge` section includes the read-only allowlist, blocked write methods, reviewed-write wrapper names, and the apply rule for repeating the exact reviewed method, path, and params.

It also includes `tool_protocol_bridge.forward_tools`: a ready wrapper map for tool-protocol hosts. Each entry gives the host-facing tool name, AKBP JSONL method, method-parameter schema reference, and response fields the bridge should preserve in its own response. Use that map when generating tool-protocol tools, IDE commands, or local assistant actions instead of inventing a second memory contract.

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

## Bridge contract

The bridge is translation glue only. It should not create another durable memory format.

Required behavior:

- Call `akbp.capabilities` at startup and require `read_only` plus `startup_context` for the first bridge.
- Generate read-only host wrappers from `tool_protocol_bridge.forward_tools` when available, preserving each entry's `method`, `params_schema`, and `surface_fields`.
- Use the generated `maintenance` checks to verify sources, rerun `akbp.doctor`, check export bundles, and refresh retrieval after approved writes instead of treating setup as a one-time install.
- Pass a caller-selected local knowledge-base path instead of hard-coding a private machine path.
- Enforce bounded requests before forwarding to the JSONL server.
- Return AKBP response envelopes or preserve `ok`, `result`, and `error.code` in the host response.
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
