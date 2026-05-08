# Tool error handling example

This example shows how an agent runtime should handle AKBP JSONL tool-server failures without guessing from free-form text.

## Request handling rules

1. Treat `ok: false` as authoritative.
2. Branch on `error.code`, not on human-readable `error.message`.
3. Do not retry write methods unless the caller supplies explicit approval when required.
4. Never store raw request text from invalid JSON errors.
5. Surface `error.details` to the runtime review layer when present.
6. Keep request ids stable so callers can match failures to their original request.

## Expected error codes

| Code | Meaning | Runtime behavior |
| --- | --- | --- |
| `invalid_json` | The line was not valid JSON. | Drop or quarantine the line without echoing raw content. |
| `invalid_request` | The JSON envelope was missing required shape. | Ask the caller to repair the envelope. |
| `unknown_method` | The method is not advertised by `akbp.capabilities`. | Re-read capabilities before retrying. |
| `invalid_params` | Method params failed schema-backed validation. | Fix params before retrying. |
| `approval_required` | A non-dry-run write was requested without approval. | Show the planned write and require explicit approval. |
| `cli_error` | The reference CLI rejected the operation. | Surface details and stop the current operation. |
| `internal_error` | The server failed unexpectedly. | Stop, preserve the request id, and report the failure. |

## Safe retry pattern

```jsonl
{"id":"caps-1","method":"akbp.capabilities"}
{"id":"preview-1","method":"akbp.remember","dry_run":true,"params":{"text":"Release needs a rollback owner."}}
{"id":"apply-1","method":"akbp.remember","approved":true,"params":{"text":"Release needs a rollback owner."}}
```

For write methods, the preview response is the review artifact. The approved request should only be sent after runtime or user policy accepts that artifact.
