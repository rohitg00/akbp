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
AKBP structured output harness example passed
```

## What it proves

- every response keeps the stable `id`, `ok`, `result`, and `error` envelope
- capability negotiation advertises schema-backed params, structured errors, and reviewed-write policy
- adapter readiness exposes the dry-run and approval boundary before writes are enabled
- startup context includes cited records before the adapter uses memory in a plan
- dry-run write previews include `review_required`, `apply_instruction`, and `would_write`
- unapproved writes return the structured `approval_required` stop signal

Use this as a starting harness before wiring AKBP into an editor command, local coding agent, or tool bridge. The adapter should branch on fields and error codes, not on free-form text.
