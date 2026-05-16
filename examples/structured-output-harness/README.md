# Structured output harness

This example shows adapter authors how to fail closed on AKBP JSONL responses before trusting recalled context or applying durable writes.

Run it from the repository root:

```bash
./examples/structured-output-harness/run.sh
```

To run the same contract as a benchmark slice against the real CLI and JSONL
tool server, use:

```bash
make adapter-quality
```

To run both the example and the focused benchmark as one adapter preflight, use:

```bash
make adapter-harness
```

Expected success markers:

```text
AKBP structured output harness example
capability contract ok
unsupported capability gate ok
invalid params repair contract ok
doctor contract ok
startup context contract ok
budget truncation contract ok
dry-run review contract ok
approval-required contract ok
approved apply contract ok
approved recall contract ok
prompt and repair contract harness ok
AKBP structured output harness example passed
```

Generated `akbp client-config` includes these markers in
`harness_adoption_fit.minimum_gate.success_markers` and
`adapter_contract_harness.success_markers`, so adapter installers can verify the
preflight by checking stdout instead of hard-coding a separate marker list.

## Response snippets adapters should preserve

Use these as copyable shape checks in host adapters. Field values such as ids,
paths, claim ids, and counts will vary, but the envelope and decision fields
must be preserved.

Capability negotiation succeeds only when every required feature and profile is
available:

```json
{
  "id": "caps",
  "ok": true,
  "result": {
    "features": {
      "method_param_schemas": true,
      "structured_errors": true,
      "write_apply_requires_approval": true
    },
    "negotiation": {
      "satisfied": true,
      "unsupported_features": [],
      "unsupported_profiles": []
    },
    "profiles": {
      "startup_context": ["akbp.capabilities", "akbp.status", "akbp.session.start", "akbp.context", "akbp.search"],
      "reviewed_write": ["akbp.remember", "akbp.ingest", "akbp.session.end"]
    }
  },
  "error": null
}
```

Invalid adapter payloads are repairable when the response keeps the schema
reference and typed field errors:

```json
{
  "id": "session-start-invalid-params",
  "ok": false,
  "result": null,
  "error": {
    "code": "invalid_params",
    "message": "Invalid params for akbp.session.start",
    "details": {
      "params_schema": "schemas/tool-methods.schema.json#/$defs/akbp.session.start.params",
      "type_errors": ["limit must be between 1 and 100"]
    }
  }
}
```

Startup context is trustworthy only when the adapter receives cited items and
preserves the budget object:

```json
{
  "id": "session-start",
  "ok": true,
  "result": {
    "session_id": "session_...",
    "task": "adapter structured output harness",
    "context": {
      "items": [
        {
          "type": "claim",
          "id": "claim_...",
          "summary": "Adapters should validate structured AKBP responses before trusting memory.",
          "citations": [{"source_id": "source_...", "locator": "harness-note.md"}]
        }
      ],
      "budget": {
        "max_chars": 500,
        "items_before_budget": 1,
        "items_after_budget": 1
      },
      "warnings": []
    }
  },
  "error": null
}
```

When context is clipped by the requested prompt budget, adapters must preserve
the truncation diagnostics and fail closed before planning from partial memory:

```json
{
  "id": "session-start-truncated",
  "ok": true,
  "result": {
    "context": {
      "items": [{"summary": "Adapters should validate..."}],
      "budget": {
        "max_chars": 24,
        "truncated": true,
        "truncated_items": 1,
        "items_before_budget": 1,
        "items_after_budget": 1
      },
      "warnings": ["Context budget truncated: clipped 1 item(s) and omitted 2 item(s); increase max_chars or lower limit for more detail."],
      "quality": {
        "ok": true,
        "require_citations": true
      }
    }
  },
  "error": null
}
```

Dry-run write previews must expose enough review metadata for a user or trusted
policy to approve the exact apply:

```json
{
  "id": "remember-preview",
  "ok": true,
  "result": {
    "dry_run": true,
    "review_required": true,
    "method": "akbp.remember",
    "path": "/path/to/kb",
    "would_write": true,
    "would_write_paths": ["claims/claims.jsonl", ".akbp/audit.log.jsonl"],
    "apply_instruction": "Repeat the same request with approved:true after review.",
    "redacted": false
  },
  "error": null
}
```

Unapproved writes are a hard stop, not a warning:

```json
{
  "id": "remember-blocked",
  "ok": false,
  "result": null,
  "error": {
    "code": "approval_required",
    "message": "Write requires dry-run review before approved apply",
    "details": {
      "method": "akbp.remember",
      "dry_run": false,
      "review_required": true,
      "apply_instruction": "Preview with dry_run:true, then repeat the reviewed request with approved:true."
    }
  }
}
```

Generated client configs also include a repair map. Adapters may retry only
schema or envelope mistakes they can fix locally; trust and approval failures
must stop memory use or writes:

```json
{
  "structured_output_repair": {
    "format": "akbp-structured-output-repair-v1",
    "max_local_repair_attempts": 1,
    "repair_attempt_scope": "per request id, method, path, and params fingerprint",
    "retryable_after_local_fix": [
      {"error_code": "invalid_json", "fix": "repair JSON serialization and resend the same intent without approved:true"},
      {"error_code": "invalid_request", "fix": "repair the JSONL envelope, request id, method, path, or unknown request-level fields"},
      {"error_code": "invalid_params", "fix": "repair params using error.details.params_schema, missing fields, unknown fields, and type_errors"},
      {"error_code": "unknown_method", "fix": "refresh akbp.capabilities, then disable unavailable methods when still missing"}
    ],
    "never_auto_repair": [
      "approval_required",
      "startup context without citations",
      "startup context with unsurfaced warnings",
      "truncated context budget during startup trust gate"
    ],
    "write_retry_rule": "After any request or params repair, rerun write-capable methods as dry_run:true and require a fresh review before approved:true apply.",
    "exhausted_retry_action": "Stop after the local repair budget is exhausted, surface the structured error, and keep AKBP read-only for that flow."
  }
}
```

## What it proves

- every response keeps the stable `id`, `ok`, `result`, and `error` envelope
- capability negotiation advertises schema-backed params, structured errors, and reviewed-write policy
- unsupported capability or profile requests leave `negotiation.satisfied:false` so adapters can disable unavailable flows before planning
- invalid adapter payloads return `invalid_params` with a method schema reference and concrete field errors the adapter can use for repair
- generated client config exposes which structured errors are locally repairable and which trust or approval failures must stop memory use or writes
- adapter readiness exposes the dry-run and approval boundary before writes are enabled
- startup context includes cited records before the adapter uses memory in a plan
- startup context budget truncation exposes `budget.truncated`,
  `truncated_items`, and warnings that adapters can use to fail closed before
  planning from partial memory
- dry-run write previews include `review_required`, `apply_instruction`, and `would_write`
- dry-run write previews include `preview_fingerprint` so adapters can bind
  the later approved apply to the reviewed method, path, and params
- unapproved writes return the structured `approval_required` stop signal
- approved writes return a schema-backed claim only after the review gate is
  crossed, and indexed recall can cite the approved memory
- generated client config includes a prompt contract and first-run checklist
  that force adapters to retrieve cited startup context, branch on
  `error.code`, preserve budget warnings, and keep writes behind a visible
  review surface

## Adapter confidence scorecard

Use this scorecard when the harness passes but you still need to decide whether
an adapter is ready for real memory traffic. Do not collapse it to a short
generic checklist. A bridge can preserve JSON shape and still be unsafe if it
ignores citations, warnings, approval boundaries, or unsupported profiles.

| Gate | Pass condition | Fail closed when |
|------|----------------|------------------|
| Envelope | Every response has exactly `id`, `ok`, `result`, and `error`, and the adapter branches on `ok` before reading nested fields. | The host treats malformed JSON, missing fields, or `ok:false` as usable memory. |
| Capability negotiation | `result.negotiation.satisfied` is true for the requested features and profiles before the adapter enables that flow. | The host silently falls back from a missing profile to a weaker memory mode. |
| Repairable params | `invalid_params` includes `params_schema` and concrete `type_errors` that the bridge can map back to its payload. | The host retries by changing free-form prompt text instead of fixing the structured request. |
| Repair map | `structured_output_repair` marks `invalid_json`, `invalid_request`, `invalid_params`, and `unknown_method` as locally repairable, caps local repair at one attempt per request fingerprint, and keeps trust or approval failures non-retryable. | The host asks the model to continue after a trust or approval failure, loops on repeated repairs, or resends a write as `approved:true` after repairing params without a fresh dry-run review. |
| Startup trust | `akbp.session.start` returns at least one cited item, preserves `result.context.budget`, and surfaces warnings or truncation. | Context is empty, uncited, over budget, or warning-bearing and the runtime still plans from recalled memory. |
| Review preview | Dry-run writes expose `review_required`, `would_write`, `would_write_paths`, `redacted`, `preview_fingerprint`, and `apply_instruction` to the review surface. | The user or policy cannot inspect or fingerprint the exact durable change before approval. |
| Approval stop | Non-dry-run writes without `approved:true` return `error.code:"approval_required"` and the adapter stops. | The adapter logs a warning, asks the model to continue, or writes to another memory store. |
| Approved apply | The approved request matches the reviewed preview and returns schema-backed records with cited evidence. | The apply changes text, evidence, scope, or target path after review. |
| Recalled proof | After indexing, the same reviewed claim is retrievable with citations for the task that needs it. | The write succeeds but the next startup context cannot cite or retrieve it. |
| Prompt contract | Generated `adapter_prompt_contract.system_rules` and validation fields are preserved in the runtime instructions. | The host turns AKBP guidance into prose that loses field names, stop conditions, or `error.code` handling. |

Minimum bar: all gates pass in `examples/structured-output-harness/run.sh`
and the focused benchmark passes through `make adapter-quality`. Keep the
adapter read-only until failures are fixed at the structured-response boundary,
not hidden behind more prompting.

Use this as a starting harness before wiring AKBP into an editor command, local coding agent, or tool bridge. The adapter should branch on fields and error codes, not on free-form text.

Run this after the session-start harness and before enabling reviewed writes.
Treat a failure here as an adapter-contract failure, even if the lower-level CLI
or JSONL smoke tests pass.

## Adapter stop conditions

An adapter should stay read-only or setup-only when this harness cannot prove:

- capability negotiation satisfies the profiles the adapter requires
- unsupported feature or profile negotiation disables that flow instead of falling through to a weaker memory mode
- invalid params include the method schema reference and typed errors needed to repair the adapter payload
- doctor readiness says the selected knowledge base is safe for adapter use
- startup context includes cited items before the runtime plans from memory
- write previews expose review metadata and planned durable changes
- unapproved apply attempts stop with `error.code:"approval_required"`
- approved apply plus index refresh returns cited recall for the same reviewed
  durable claim
- the generated prompt contract gives the runtime concrete system rules for
  cited startup context, dry-run previews, exact approved apply, and
  fail-closed error handling

These checks keep AKBP as a reviewable knowledge contract instead of an opaque
memory sidecar.
