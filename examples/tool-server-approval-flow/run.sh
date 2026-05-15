#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
KB="${1:-$(mktemp -d)/akbp-tool-server-approval-kb}"
EXPORT="$KB/export.jsonl"

echo "AKBP tool-server approval flow"
echo "kb=$KB"

python3 "$ROOT/cli/akbp.py" --path "$KB" init >/dev/null

CAPS="$(printf '%s\n' '{"id":"caps","method":"akbp.capabilities","path":"'"$KB"'","params":{"client":"approval-flow-example","requires":["method_param_schemas","capability_negotiation","write_apply_requires_approval"],"requires_profiles":["startup_context","reviewed_write"]}}' \
  | python3 "$ROOT/tool-server/akbp_tool_server.py")"
printf '%s\n' "$CAPS" | python3 -c 'import json,sys; row=json.loads(sys.stdin.readline()); assert row["ok"], row; n=row["result"]["negotiation"]; assert n["satisfied"], n; assert n["unsupported_features"] == [], n; assert n["unsupported_profiles"] == [], n; assert "startup_context" in n["supported_profiles"], n; assert row["result"]["features"]["method_param_schemas"]; assert row["result"]["features"]["write_apply_requires_approval"]; print("capabilities ok")'

WRITE_PARAMS='{"text":"Agents need rollback paths before production changes","type":"workflow","evidence":["release-review.md"]}'
WRITE_JSON="$(printf '%s\n' \
  '{"id":"remember-preview","method":"akbp.remember","path":"'"$KB"'","dry_run":true,"params":'"$WRITE_PARAMS"'}' \
  '{"id":"remember-unapproved","method":"akbp.remember","path":"'"$KB"'","params":'"$WRITE_PARAMS"'}' \
  '{"id":"remember-bad-type","method":"akbp.remember","path":"'"$KB"'","dry_run":true,"params":{"text":"Agents need rollback paths before production changes","type":"runbook"}}' \
  '{"id":"remember-approved","method":"akbp.remember","path":"'"$KB"'","approved":true,"params":'"$WRITE_PARAMS"'}' \
  | python3 "$ROOT/tool-server/akbp_tool_server.py")"
printf '%s\n' "$WRITE_JSON" | python3 -c 'import json,sys; rows={row["id"]:row for row in (json.loads(line) for line in sys.stdin if line.strip())}; preview=rows["remember-preview"]; assert preview["ok"], preview; assert preview["result"]["dry_run"]; assert preview["result"]["review_required"]; assert "apply_instruction" in preview["result"]; blocked=rows["remember-unapproved"]; assert not blocked["ok"], blocked; assert blocked["error"]["code"]=="approval_required"; assert blocked["error"]["details"]["review_required"]; bad=rows["remember-bad-type"]; assert not bad["ok"], bad; assert bad["error"]["code"]=="invalid_params"; approved=rows["remember-approved"]; assert approved["ok"], approved; assert approved["result"]["id"].startswith("claim_"), approved; print("reviewed remember flow ok")'
test "$(python3 -c 'import json,sys,pathlib; p=pathlib.Path(sys.argv[1]); rows=[json.loads(line) for line in p.read_text().splitlines() if line.strip()]; print(len(rows))' "$KB/claims/claims.jsonl")" = "1"

cat > "$EXPORT" <<'JSONL'
{"kind":"source","id":"source_import_reviewed","type":"transcript","locator":"imports/reviewed.md","title":"Reviewed import"}
{"kind":"claim","id":"claim_import_reviewed","text":"Reviewed JSONL imports require a dry-run preview before apply.","type":"workflow","status":"working","confidence":0.8,"evidence":["source_import_reviewed"]}
JSONL

IMPORT_JSON="$(printf '%s\n' \
  '{"id":"import-check","method":"akbp.import_check","path":"'"$KB"'","params":{"file":"'"$EXPORT"'"}}' \
  '{"id":"import-preview","method":"akbp.import_apply","path":"'"$KB"'","dry_run":true,"params":{"file":"'"$EXPORT"'"}}' \
  '{"id":"import-approved","method":"akbp.import_apply","path":"'"$KB"'","approved":true,"params":{"file":"'"$EXPORT"'"}}' \
  '{"id":"index-approved","method":"akbp.index","path":"'"$KB"'","approved":true,"params":{"incremental":true}}' \
  '{"id":"context","method":"akbp.context","path":"'"$KB"'","params":{"task":"prepare production release with reviewed JSONL imports","limit":5}}' \
  | python3 "$ROOT/tool-server/akbp_tool_server.py")"
printf '%s\n' "$IMPORT_JSON" | python3 -c 'import json,sys; rows={row["id"]:row for row in (json.loads(line) for line in sys.stdin if line.strip())}; check=rows["import-check"]; assert check["ok"], check; assert check["result"]["accepted_count"] == 2, check; preview=rows["import-preview"]; assert preview["ok"], preview; assert preview["result"]["dry_run"]; assert preview["result"]["review_required"]; assert preview["result"]["would_write"]["sources"] == ["source_import_reviewed"], preview; assert preview["result"]["would_write"]["claims"] == ["claim_import_reviewed"], preview; approved=rows["import-approved"]; assert approved["ok"], approved; assert approved["result"]["applied"]; indexed=rows["index-approved"]; assert indexed["ok"], indexed; ctx=rows["context"]; assert ctx["ok"], ctx; assert ctx["result"]["items"], ctx; print("reviewed import flow ok")'

python3 "$ROOT/cli/akbp.py" --path "$KB" conformance --level 2 >/dev/null

echo "AKBP tool-server approval flow passed"
