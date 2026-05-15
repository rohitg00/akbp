# GitHub Copilot Session End

Use this sequence when a session produced durable project knowledge.

## 1. Create a local summary

Write a concise local summary that includes only durable facts:

- decisions
- changed workflows
- resolved blockers
- source-backed preferences
- open questions

Exclude secrets, tokens, cookies, auth headers, private messages, and raw logs with credentials.

## 2. Preview crystallization

```json
{"id":"copilot-session-end-preview","method":"akbp.session.end","path":".","dry_run":true,"params":{"transcript":"session-summary.md","apply":true}}
```

Show `review_required`, `apply_instruction`, accepted and rejected object counts, warnings, and would-write paths.

## 3. Apply only after approval

```json
{"id":"copilot-session-end-apply","method":"akbp.session.end","path":".","approved":true,"params":{"transcript":"session-summary.md","apply":true}}
```

Refresh retrieval after approved writes:

```json
{"id":"copilot-index","method":"akbp.index","path":".","approved":true,"params":{"incremental":true}}
```

Follow `docs/AGENT_FLOW.md` for the canonical shutdown loop.
