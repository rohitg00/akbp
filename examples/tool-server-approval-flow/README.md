# Tool Server Approval Flow Example

This example shows the safe JSONL write path for local agent integrations.

The rule is simple:

1. discover capabilities and method parameter schemas first
2. preview write-capable calls with request-level `dry_run:true`
3. render `review_required` and `apply_instruction` to the user or calling runtime
4. apply only after approval with request-level `approved:true`
5. expect `approval_required` when a non-dry-run write omits approval

## Setup

Run from the repository root:

```bash
TMP_KB="$(mktemp -d)"
python3 cli/akbp.py --path "$TMP_KB" init
```

## Discover capabilities and schemas

Adapters should start each process or session by asking the server what it
supports. This keeps clients from hard-coding write policy, schema locations, or
method names that may drift.

```bash
printf '%s\n' '{"id":"caps","method":"akbp.capabilities","params":{"client":"approval-flow-example","requires":["method_param_schemas","capability_negotiation","write_apply_requires_approval"]}}' \
  | python3 tool-server/akbp_tool_server.py
```

Expected behavior:

- `ok:true`
- `result.negotiation.satisfied:true`
- every advertised method includes `write` and, when available, `params_schema`
- `result.features.method_param_schemas:true`
- `result.features.write_apply_requires_approval:true`

If `result.negotiation.satisfied:false`, the adapter should gracefully disable
the flows that depend on the unsupported feature instead of guessing.

## Preview a write

```bash
printf '%s\n' '{"id":"remember-preview","method":"akbp.remember","path":"'"$TMP_KB"'","dry_run":true,"params":{"text":"Agents need rollback paths before production changes","type":"workflow","evidence":["release-review.md"]}}' \
  | python3 tool-server/akbp_tool_server.py
```

Expected behavior:

- `ok:true`
- `result.dry_run:true`
- `result.review_required:true`
- `result.apply_instruction` explains when to repeat the request
- the knowledge base is not mutated

The response matches the `#/$defs/dry_run_review_result` shape from `schemas/tool-response.schema.json`:

```json
{
  "id": "remember-preview",
  "ok": true,
  "result": {
    "dry_run": true,
    "method": "akbp.remember",
    "would_write": true,
    "redacted": false,
    "review_required": true,
    "apply_instruction": "Repeat the same request without dry_run only after user approval or trusted local policy."
  },
  "error": null
}
```

## Rejected apply without approval

```bash
printf '%s\n' '{"id":"remember-unapproved","method":"akbp.remember","path":"'"$TMP_KB"'","params":{"text":"Agents need rollback paths before production changes","type":"workflow","evidence":["release-review.md"]}}' \
  | python3 tool-server/akbp_tool_server.py
```

Expected behavior:

- `ok:false`
- `error.code:"approval_required"`
- `error.details.review_required:true`
- `error.details.apply_instruction` tells the caller to repeat with `approved:true` after approval or trusted local policy

The response matches the `#/$defs/approval_required_details` shape from `schemas/tool-response.schema.json`:

```json
{
  "id": "remember-unapproved",
  "ok": false,
  "result": null,
  "error": {
    "code": "approval_required",
    "message": "akbp.remember requires approved:true for non-dry-run writes",
    "details": {
      "method": "akbp.remember",
      "dry_run": false,
      "review_required": true,
      "apply_instruction": "Repeat the same request with approved:true only after user approval or trusted local policy."
    }
  }
}
```

## Rejected invalid params before CLI dispatch

Method-specific schemas reject malformed requests before they reach the CLI. The
caller should repair the request, not retry it with approval.

```bash
printf '%s\n' '{"id":"remember-bad-type","method":"akbp.remember","path":"'"$TMP_KB"'","dry_run":true,"params":{"text":"Agents need rollback paths before production changes","type":"runbook"}}' \
  | python3 tool-server/akbp_tool_server.py
```

Expected behavior:

- `ok:false`
- `error.code:"invalid_params"`
- `error.details.schema` references `tool-methods.schema.json#/$defs/akbp.remember.params`
- the knowledge base is not mutated

Do not convert an `invalid_params` response into an approved write. Fix the
payload until the dry-run preview succeeds.

## Apply after approval

```bash
printf '%s\n' '{"id":"remember-approved","method":"akbp.remember","path":"'"$TMP_KB"'","approved":true,"params":{"text":"Agents need rollback paths before production changes","type":"workflow","evidence":["release-review.md"]}}' \
  | python3 tool-server/akbp_tool_server.py
```

Expected behavior:

- `ok:true`
- the claim is appended to `claims/claims.jsonl`

The approved request should keep the same `method`, `path`, and `params` as the
reviewed dry-run. Only the request id and envelope policy fields should change:
remove `dry_run:true` and add request-level `approved:true` after user approval
or trusted local policy.


## Import a reviewed JSONL export

Validate exports before applying them:

```bash
cat > "$TMP_KB/export.jsonl" <<'JSONL'
{"kind":"source","id":"source_import_reviewed","type":"transcript","locator":"imports/reviewed.md","title":"Reviewed import"}
{"kind":"claim","id":"claim_import_reviewed","text":"Reviewed JSONL imports require a dry-run preview before apply.","type":"workflow","status":"working","confidence":0.8,"evidence":["source_import_reviewed"]}
JSONL

printf '%s\n' '{"id":"import-check","method":"akbp.import_check","path":"'"$TMP_KB"'","params":{"file":"'"$TMP_KB"'/export.jsonl"}}' \
  | python3 tool-server/akbp_tool_server.py
```

Preview the accepted source and claim records:

```bash
printf '%s\n' '{"id":"import-preview","method":"akbp.import_apply","path":"'"$TMP_KB"'","dry_run":true,"params":{"file":"'"$TMP_KB"'/export.jsonl"}}' \
  | python3 tool-server/akbp_tool_server.py
```

Expected behavior:

- `ok:true`
- `result.dry_run:true`
- `result.applied:false`
- `result.review_required:true`
- `result.apply_instruction` tells the caller to repeat with `approved:true` after review
- `result.would_write.sources` and `result.would_write.claims` list the reviewed ids

Apply only after review:

```bash
printf '%s\n' '{"id":"import-approved","method":"akbp.import_apply","path":"'"$TMP_KB"'","approved":true,"params":{"file":"'"$TMP_KB"'/export.jsonl"}}' \
  | python3 tool-server/akbp_tool_server.py
```

## Refresh search after approved writes

Indexing mutates local state, so it is also approval-gated:

```bash
printf '%s\n' '{"id":"index-approved","method":"akbp.index","path":"'"$TMP_KB"'","approved":true,"params":{"incremental":true}}' \
  | python3 tool-server/akbp_tool_server.py
```

Then query context normally:

```bash
printf '%s\n' '{"id":"context","method":"akbp.context","path":"'"$TMP_KB"'","params":{"task":"prepare production release","limit":5}}' \
  | python3 tool-server/akbp_tool_server.py
```
