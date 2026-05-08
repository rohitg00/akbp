# Adapter author quickstart

Use this when adding AKBP support to a coding agent, IDE agent, task runner, or local assistant runtime.

The adapter's job is translation only. It should connect runtime events to AKBP reads and review-gated writes without creating a separate durable memory format.

## 1. Start from the template

Copy the runtime-neutral template:

```bash
cp -R adapters/coding-agent-template adapters/<runtime-name>
```

Required files:

```text
README.md
instructions.md
config.example.json
session-start.md
session-end.md
privacy.md
```

Keep examples public-safe. Do not include local usernames, private paths, tokens, cookies, auth headers, screenshots, private chat text, or production logs.

## 2. Discover capabilities before calling methods

An adapter should call `akbp.capabilities` at startup and cache the response for the session.

JSONL request:

```json
{"id":"caps-1","method":"akbp.capabilities"}
```

Adapter checks:

- method exists before use
- method parameter schema is advertised when validation is needed
- write policy is understood
- `dry_run` support is present for write-capable flows
- approval field is known before applying writes

Do not hard-code future methods. If a method is missing, degrade gracefully and tell the user which capability is unavailable.

## 3. Retrieve context at session start

Use `akbp.session.start` as the adapter-level session entrypoint. It wraps context retrieval and returns a stable `session_id` plus the normal context pack. Use `akbp.context` and `akbp.search` directly when the runtime needs lower-level calls.

```json
{"id":"session-start-1","method":"akbp.session.start","path":".","params":{"task":"current task goals and constraints","limit":5}}
```

Lower-level context request:

```json
{"id":"ctx-1","method":"akbp.context","path":".","params":{"task":"current task goals and constraints","limit":5}}
```

```json
{"id":"search-1","method":"akbp.search","path":".","params":{"query":"release checklist","limit":5}}
```

The adapter should show citations or source ids when prior knowledge affects a plan or answer.

## 4. Preview writes before applying

All write-capable calls must start as previews.

Example session-end preview:

```json
{"id":"session-end-preview-1","method":"akbp.session.end","path":".","dry_run":true,"params":{"transcript":"session.md","apply":true}}
```

If the response includes review metadata, surface it in the runtime UI or command output:

- `review_required`
- `apply_instruction`
- accepted/rejected object counts
- source/evidence warnings

Apply only after approval or an explicit trusted local policy:

```json
{"id":"session-end-apply-1","method":"akbp.session.end","path":".","approved":true,"params":{"transcript":"session.md","apply":true}}
```

## 5. Preserve evidence and auditability

When importing source material, prefer source registration plus ingest preview:

```json
{"id":"source-1","method":"akbp.source.add","path":".","params":{"locator":"notes/session.md","type":"file","title":"Session notes"}}
```

```json
{"id":"ingest-preview-1","method":"akbp.ingest","path":".","dry_run":true,"params":{"file":"notes/session.md"}}
```

Verify local file evidence before depending on it:

```json
{"id":"verify-1","method":"akbp.source.verify","path":".","params":{}}
```

Never convert secrets or raw private logs into durable AKBP records.

## 6. Handle structured errors

Branch on `error.code`, not free-form messages.

Common codes an adapter should handle:

- `approval_required`: show the preview and ask for approval before retrying with `approved:true`.
- `unknown_method`: refresh capabilities and disable that flow.
- `invalid_params`: show the schema-backed parameter issue.
- `cli_error`: show the command failure without leaking sensitive input.

See `examples/tool-error-handling/README.md`.

## 7. Validate the adapter before publishing

Run:

```bash
make validate
```

Then review:

- `docs/ADAPTER_REVIEW_CHECKLIST.md`
- `docs/AGENT_FLOW.md`
- `docs/TOOL_CONTRACT.md`
- `examples/tool-server-approval-flow/README.md`

## Publication bar

An adapter is publishable when:

- it uses `akbp.capabilities` before method assumptions
- startup retrieves cited context
- writes are dry-run first and approval-gated
- session-end memory uses `akbp.session.end` or `akbp.crystallize_session` where possible
- private data and secrets are excluded by default
- examples are copy-pasteable and public-safe
- `make validate` passes
