# Tool Server Approval Flow Example

This example shows the safe JSONL write path for local agent integrations.

The rule is simple:

1. preview write-capable calls with request-level `dry_run:true`
2. render `review_required` and `apply_instruction` to the user or calling runtime
3. apply only after approval with request-level `approved:true`
4. expect `approval_required` when a non-dry-run write omits approval

## Setup

Run from the repository root:

```bash
TMP_KB="$(mktemp -d)"
python3 cli/akbp.py --path "$TMP_KB" init
```

## Preview a write

```bash
printf '%s\n' '{"id":"remember-preview","method":"akbp.remember","path":"'"$TMP_KB"'","dry_run":true,"params":{"text":"Agents need rollback paths before production changes","type":"policy","evidence":["release-review.md"]}}' \
  | python3 tool-server/akbp_tool_server.py
```

Expected behavior:

- `ok:true`
- `result.dry_run:true`
- `result.review_required:true`
- `result.apply_instruction` explains when to repeat the request
- the knowledge base is not mutated

## Rejected apply without approval

```bash
printf '%s\n' '{"id":"remember-unapproved","method":"akbp.remember","path":"'"$TMP_KB"'","params":{"text":"Agents need rollback paths before production changes","type":"policy","evidence":["release-review.md"]}}' \
  | python3 tool-server/akbp_tool_server.py
```

Expected behavior:

- `ok:false`
- `error.code:"approval_required"`
- `error.details.review_required:true`
- `error.details.apply_instruction` tells the caller to repeat with `approved:true` after approval or trusted local policy

## Apply after approval

```bash
printf '%s\n' '{"id":"remember-approved","method":"akbp.remember","path":"'"$TMP_KB"'","approved":true,"params":{"text":"Agents need rollback paths before production changes","type":"policy","evidence":["release-review.md"]}}' \
  | python3 tool-server/akbp_tool_server.py
```

Expected behavior:

- `ok:true`
- the claim is appended to `claims/claims.jsonl`

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
