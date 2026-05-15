# Adapter lifecycle example

This example shows the minimal JSONL flow an adapter can wire into a coding-agent session lifecycle.

Use this when the runtime has a clear startup and shutdown hook. It is deliberately local-first and review-gated: startup reads context, shutdown previews durable memory, and apply requires explicit approval.

Run the full lifecycle check:

```bash
./examples/adapter-lifecycle/run.sh
```

Expected success markers:

```text
AKBP adapter lifecycle example
capabilities ok
session start ok
session end preview ok
unapproved session end blocked
session end apply ok
lifecycle recall ok
AKBP adapter lifecycle example passed
```

## 1. Start the session with retrieved context

Send a JSONL request to the AKBP tool server:

```json
{"id":"lifecycle-start","method":"akbp.session.start","path":".","params":{"task":"prepare the release candidate","limit":5}}
```

The response includes:

- `session_id`
- the normalized `task`
- a context pack from the same retrieval path as `akbp.context`

Adapters should show or inject this context before planning. Do not treat an empty context pack as failure; it just means no relevant durable claims were found yet.

## 2. Preview shutdown memory before writing

Write a short session summary, then preview crystallization:

```json
{"id":"lifecycle-end-preview","method":"akbp.session.end","path":".","dry_run":true,"params":{"transcript":"examples/adapter-lifecycle/session-summary.md","apply":true}}
```

The preview response is the review surface. It includes the extracted summary, planned page path, `would_write`, `review_required`, `apply_instruction`, and any skipped claims.

Adapters must stop here until a user or trusted local policy approves the durable write.

## 3. Apply only after review

After approval, repeat the same request with `approved:true` and without request-level dry-run:

```json
{"id":"lifecycle-end-apply","method":"akbp.session.end","path":".","approved":true,"params":{"transcript":"examples/adapter-lifecycle/session-summary.md","apply":true}}
```

After a successful apply, refresh retrieval if the integration does not do it automatically:

```json
{"id":"lifecycle-index","method":"akbp.index","path":".","approved":true,"params":{"incremental":true}}
```

Then retrieve again before relying on the newly written memory:

```json
{"id":"lifecycle-recall","method":"akbp.context","path":".","params":{"task":"continue adapter lifecycle integration","limit":5}}
```

## Adapter contract

- Call `akbp.capabilities` first and check `akbp.session.start`, `akbp.session.end`, and `params_schema` references.
- Use `akbp.session.start` for startup retrieval.
- Use `akbp.session.end` for shutdown memory.
- Start shutdown with `dry_run:true`.
- Require `approved:true` before durable apply.
- Render `review_required`, `apply_instruction`, skipped claims, and planned writes.
- Keep private logs out of durable memory unless they have been summarized and reviewed.
