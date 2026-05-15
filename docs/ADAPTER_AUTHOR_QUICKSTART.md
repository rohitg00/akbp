# Adapter author quickstart

Use this when adding AKBP support to a coding agent, IDE agent, task runner, or local assistant runtime.

The adapter's job is translation only. It should connect runtime events to AKBP reads and review-gated writes without creating a separate durable memory format.

## 1. Generate a read-only client config first

Start with a read-only config when you are evaluating a runtime or wiring a new host. It proves startup retrieval and capability negotiation without granting durable write access.

```bash
python3 cli/akbp.py --path ./my-kb init
python3 cli/akbp.py --path ./my-kb client-config --name my-adapter --profile read-only
```

The generated config includes the server command, knowledge-base path, startup `akbp.capabilities` request, required workflow profile, `akbp.doctor` health check, session-start method, and safety rules. Paste that into the host runtime, then confirm the adapter can call `akbp.capabilities`, `akbp.doctor`, and `akbp.session.start` before adding write flows.

Use reviewed writes only after the runtime can show a preview and collect approval:

```bash
python3 cli/akbp.py --path ./my-kb client-config --name my-adapter --profile reviewed-writes
```

That profile still requires review-gated writes. The adapter must surface `dry_run:true` previews, warnings, would-write paths, and the `apply_instruction`, then repeat the same method/path/params with `approved:true` after approval.

## 2. Start from the template

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

## 3. Discover capabilities before calling methods

An adapter should call `akbp.capabilities` at startup and cache the response for the session. Adapter config examples expose a `lifecycle` block that maps runtime hooks to `akbp.session.start` and `akbp.session.end`; keep that mapping explicit so users can audit what writes may happen at shutdown.

JSONL request:

```json
{"id":"caps-1","method":"akbp.capabilities","params":{"client":"example-adapter","requires":["method_param_schemas","capability_negotiation","write_apply_requires_approval"],"requires_profiles":["read_only","startup_context"]}}
```

The response includes `result.negotiation.satisfied`. If it is `false`, disable or degrade the flows named in `unsupported_features` or `unsupported_profiles` instead of guessing.

Adapter checks:

- method exists before use
- method parameter schema is advertised when validation is needed
- write policy is understood
- `dry_run` support is present for write-capable flows
- approval field is known before applying writes

Do not hard-code future methods. If a method is missing, degrade gracefully and tell the user which capability is unavailable.

Minimum startup gate:

1. Call `akbp.capabilities`.
2. Confirm `result.negotiation.satisfied` is `true` for required features.
3. Confirm required workflow profiles such as `read_only` or `startup_context` are present in `result.negotiation.supported_profiles`.
4. Call `akbp.doctor` and show `next_steps` if `ready_for_adapter` is `false`.
5. Confirm `result.features.method_schema_runtime_parity` is `true`.
6. Confirm `result.runtime.method_schema_runtime_errors` is empty.
7. Confirm the write method you plan to call advertises `review_required:true`.

If any check fails, leave read-only mode enabled and explain the missing capability instead of attempting writes.

## 4. Retrieve context at session start

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

## 5. Preview writes before applying

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

Adapter write state machine:

```text
read-only startup
  -> dry-run preview request
  -> render preview, warnings, would-write paths, and apply_instruction
  -> wait for user approval or trusted local policy
  -> repeat the same method/path/params with approved:true and without dry_run
  -> run akbp.index with approved:true when retrieval state should refresh
  -> fetch context/search again before relying on the new memory
```

Safety rules:

- Never send both `dry_run:true` and `approved:true` in the same request.
- Do not silently alter `params` between preview and apply.
- Do not auto-apply `akbp.session.end` just because a session is closing.
- Treat `approval_required` as a stop signal, not a warning.
- Show redacted CLI output as redacted; do not retry with raw secrets.

## 6. Preserve evidence and auditability

When importing source material, prefer source registration plus ingest preview.
Both operations are write-capable, so preview them before applying:

```json
{"id":"source-preview-1","method":"akbp.source.add","path":".","dry_run":true,"params":{"locator":"notes/session.md","type":"file","title":"Session notes"}}
```

```json
{"id":"source-apply-1","method":"akbp.source.add","path":".","approved":true,"params":{"locator":"notes/session.md","type":"file","title":"Session notes"}}
```

```json
{"id":"ingest-preview-1","method":"akbp.ingest","path":".","dry_run":true,"params":{"file":"notes/session.md"}}
```

```json
{"id":"ingest-apply-1","method":"akbp.ingest","path":".","approved":true,"params":{"file":"notes/session.md"}}
```

Verify local file evidence before depending on it:

```json
{"id":"verify-1","method":"akbp.source.verify","path":".","params":{"source_id":"source_..."}}
```

Never convert secrets or raw private logs into durable AKBP records.

## 7. Handle structured errors

Branch on `error.code`, not free-form messages.

Common codes an adapter should handle:

- `approval_required`: show the preview and ask for approval before retrying with `approved:true`.
- `unknown_method`: refresh capabilities and disable that flow.
- `invalid_params`: show the schema-backed parameter issue.
- `cli_error`: show the command failure from the redacted message/stdout, and use `redacted` to explain that sensitive-looking values were hidden.

See `examples/tool-error-handling/README.md`.

## 8. Validate the adapter before publishing

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
