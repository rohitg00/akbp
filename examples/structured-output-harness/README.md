# Structured output harness

This example shows adapter authors how to fail closed on AKBP JSONL responses before trusting recalled context or applying durable writes.

Run it from the repository root:

```bash
./examples/structured-output-harness/run.sh
```

Expected success markers:

```text
AKBP structured output harness example
capability contract ok
doctor contract ok
startup context contract ok
dry-run review contract ok
approval-required contract ok
approved apply contract ok
approved recall contract ok
AKBP structured output harness example passed
```

## What it proves

- every response keeps the stable `id`, `ok`, `result`, and `error` envelope
- capability negotiation advertises schema-backed params, structured errors, and reviewed-write policy
- adapter readiness exposes the dry-run and approval boundary before writes are enabled
- startup context includes cited records before the adapter uses memory in a plan
- dry-run write previews include `review_required`, `apply_instruction`, and `would_write`
- unapproved writes return the structured `approval_required` stop signal
- approved writes return a schema-backed claim only after the review gate is
  crossed, and indexed recall can cite the approved memory

Use this as a starting harness before wiring AKBP into an editor command, local coding agent, or tool bridge. The adapter should branch on fields and error codes, not on free-form text.

Run this after the session-start harness and before enabling reviewed writes.
Treat a failure here as an adapter-contract failure, even if the lower-level CLI
or JSONL smoke tests pass.

## Adapter stop conditions

An adapter should stay read-only or setup-only when this harness cannot prove:

- capability negotiation satisfies the profiles the adapter requires
- doctor readiness says the selected knowledge base is safe for adapter use
- startup context includes cited items before the runtime plans from memory
- write previews expose review metadata and planned durable changes
- unapproved apply attempts stop with `error.code:"approval_required"`
- approved apply plus index refresh returns cited recall for the same reviewed
  durable claim

These checks keep AKBP as a reviewable knowledge contract instead of an opaque
memory sidecar.
