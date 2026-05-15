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
dry-run review contract ok
approval-required contract ok
approved apply contract ok
approved recall contract ok
prompt contract harness ok
AKBP structured output harness example passed
```

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

## What it proves

- every response keeps the stable `id`, `ok`, `result`, and `error` envelope
- capability negotiation advertises schema-backed params, structured errors, and reviewed-write policy
- unsupported capability or profile requests leave `negotiation.satisfied:false` so adapters can disable unavailable flows before planning
- invalid adapter payloads return `invalid_params` with a method schema reference and concrete field errors the adapter can use for repair
- adapter readiness exposes the dry-run and approval boundary before writes are enabled
- startup context includes cited records before the adapter uses memory in a plan
- dry-run write previews include `review_required`, `apply_instruction`, and `would_write`
- unapproved writes return the structured `approval_required` stop signal
- approved writes return a schema-backed claim only after the review gate is
  crossed, and indexed recall can cite the approved memory
- generated client config includes a prompt contract and first-run checklist
  that force adapters to retrieve cited startup context, branch on
  `error.code`, preserve budget warnings, and keep writes behind a visible
  review surface

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
