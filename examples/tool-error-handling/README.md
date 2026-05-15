# Tool Error Handling Example

This example shows the JSONL tool-server failures an adapter should handle as
control flow. The core rule is to branch on `error.code`, not free-form error
text.

Adjacent memory tools often expose a simple server interface and let clients
guess what failed. AKBP keeps the interface small, but makes failures structured
so a coding-agent adapter can recover safely:

- `invalid_json`: repair the JSON line before retrying.
- `invalid_request`: repair the request envelope before retrying.
- `unknown_method`: refresh `akbp.capabilities` and disable that flow.
- `invalid_params`: repair parameters using the advertised method schema.
- `approval_required`: stop the apply path until a reviewed `dry_run` is approved.
- `cli_error`: show the redacted CLI failure and avoid writing partial memory.
- `internal_error`: stop and surface the bug; do not retry as a write.

## Adapter action matrix

Use this matrix when translating AKBP JSONL responses into a host runtime, tool
bridge, editor extension, or task-runner wrapper. The client should make these
decisions from `ok` and `error.code`, not from `error.message`.

| Response | Adapter action | Retry policy | User-visible state |
|----------|----------------|--------------|--------------------|
| `ok:true` read response | Use `result` and preserve citations, warnings, and budget fields. | No retry. | Show retrieved context or capability state. |
| `ok:true` `dry_run` write preview | Render `result.review_required`, `result.apply_instruction`, and planned writes for review. | Retry only as the same request with `approved:true` after approval or trusted local policy. | Show pending review, not committed memory. |
| `invalid_json` | Repair JSON serialization before sending another line. | Retry after local encoder fix. | Show adapter bug or malformed request. |
| `invalid_request` | Repair the request envelope and remove unknown request-level fields. | Retry after envelope fix. | Show adapter bug or incompatible client. |
| `unknown_method` | Refresh `akbp.capabilities`; disable unavailable flow if still missing. | Retry only after capability refresh. | Show unsupported method. |
| `invalid_params` | Use `error.details.params_schema`, missing fields, unknown fields, and type errors to repair `params`. | Retry after parameter fix. | Show invalid input. |
| `approval_required` | Stop the apply path; require a reviewed preview before applying. | Retry only with `approved:true` after approval or trusted local policy. | Show approval needed. |
| `cli_error` | Surface redacted CLI stdout/stderr and avoid assuming any durable write happened. | Retry only after the underlying CLI issue is fixed. | Show operation failed. |
| `internal_error` | Stop the flow and report a server defect. | Do not auto-retry writes. | Show integration failure. |

For write methods, an adapter should only move from preview to apply when the
method, path, and params match the reviewed request. The request id may change,
but changing the write payload after review should send the user back through a
new `dry_run:true` preview.

Run from the repository root:

```bash
./examples/tool-error-handling/run.sh
```

## Discover capabilities first

Start each integration session with capability discovery:

```json
{"id":"caps","method":"akbp.capabilities","params":{"client":"tool-error-handling-example","requires":["structured_errors","method_param_schemas","approval_required_errors"]}}
```

Expected behavior:

- `ok:true`
- `result.features.structured_errors:true`
- `result.features.method_param_schemas:true`
- `result.features.approval_required_errors:true`

## Request envelope failures

Malformed JSON returns `invalid_json`:

```text
{"id":"broken","method":"akbp.search"
```

Unknown request fields return `invalid_request`:

```json
{"id":"bad-envelope","method":"akbp.search","params":{"query":"release"},"unexpected":true}
```

Adapters should fix the envelope before retrying. Do not ask for approval,
because this is not a write-review failure.

## Method and parameter failures

Unknown methods return `unknown_method` with the advertised method list:

```json
{"id":"unknown","method":"akbp.nope","params":{}}
```

Invalid parameters return `invalid_params` with a schema reference:

```json
{"id":"bad-limit","method":"akbp.search","params":{"query":"release","limit":0}}
```

The adapter should use `error.details.params_schema` and
`error.details.type_errors` to repair the request.

## Write-control failures

Write-capable methods should be previewed with request-level `dry_run:true`:

```json
{"id":"remember-preview","method":"akbp.remember","path":"./my-kb","dry_run":true,"params":{"text":"Decision: keep reviewed writes explicit."}}
```

Applying the same write without request-level `approved:true` returns
`approval_required`:

```json
{"id":"remember-blocked","method":"akbp.remember","path":"./my-kb","params":{"text":"Decision: keep reviewed writes explicit."}}
```

Only retry the apply after the user or trusted local policy approves the preview:

```json
{"id":"remember-approved","method":"akbp.remember","path":"./my-kb","approved":true,"params":{"text":"Decision: keep reviewed writes explicit."}}
```

## CLI failures stay structured

If the underlying CLI rejects an otherwise valid request, the server returns
`cli_error` with redacted stdout/stderr and the CLI exit code. For example,
asking `akbp.cite` for a missing claim id should not become an unstructured
adapter crash:

```json
{"id":"missing-cite","method":"akbp.cite","path":"./my-kb","params":{"claim_id":"claim_missing"}}
```

Expected behavior:

- `ok:false`
- `error.code:"cli_error"`
- `error.details.exit_code` is present
- `error.details.redacted` tells the adapter whether secrets were removed

`internal_error` is reserved for unexpected tool-server defects. Treat it as a
bug report path, not a retryable memory operation.
