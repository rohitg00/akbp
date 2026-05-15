# Session-start harness

This example gives adapter authors a small harness for the first AKBP call sequence a runtime should trust.

It validates capability negotiation, the knowledge-base health check, and `akbp.session.start` before an adapter uses recalled context in a plan.

## Run

From the repository root:

```bash
examples/session-start-harness/run.sh
```

Expected success marker:

```text
AKBP session-start harness example passed
```

## What it proves

- `akbp.capabilities` satisfies the requested `read_only` and `startup_context` profiles
- `akbp.doctor` reports the knowledge base as ready for adapter use
- `akbp.session.start` returns a stable `session_id`, context items, citations, and warnings
- the adapter has a concrete stop condition when startup context is empty or uncited
- a first integration can be tested without enabling durable writes

This is the minimal harness to run before mapping AKBP into an editor command, coding-agent startup hook, or local assistant session.
