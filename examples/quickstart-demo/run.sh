#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
KB="${1:-$(mktemp -d)/akbp-demo-kb}"
NOTE="$ROOT/examples/quickstart-demo/session-note.md"
BUNDLE="$KB/export.json"

echo "AKBP quickstart demo"
echo "kb=$KB"

python3 "$ROOT/cli/akbp.py" --path "$KB" init
INGEST_REQUEST='{"file":"'"$NOTE"'","type":"file","title":"Demo session note","claim":"AKBP public alpha releases should stay small, weekly, and evidence-backed until the protocol reaches 1.0.","claim_type":"decision"}'
TOOL_JSON="$(printf '%s\n' \
  '{"id":"caps","method":"akbp.capabilities","path":"'"$KB"'","params":{"client":"quickstart-demo","requires":["method_param_schemas","capability_negotiation","write_apply_requires_approval"]}}' \
  '{"id":"ingest-preview","method":"akbp.ingest","path":"'"$KB"'","dry_run":true,"params":'"$INGEST_REQUEST"'}' \
  '{"id":"ingest-blocked","method":"akbp.ingest","path":"'"$KB"'","params":'"$INGEST_REQUEST"'}' \
  '{"id":"ingest-approved","method":"akbp.ingest","path":"'"$KB"'","approved":true,"params":'"$INGEST_REQUEST"'}' \
  '{"id":"index-approved","method":"akbp.index","path":"'"$KB"'","approved":true,"params":{"incremental":true}}' \
  | python3 "$ROOT/tool-server/akbp_tool_server.py")"
printf '%s\n' "$TOOL_JSON" | python3 -c 'import json,sys; fields=("id","ok","dry_run","review_required","would_write","created_claims","source_id","indexed","error"); rows=[json.loads(line) for line in sys.stdin if line.strip()];
for row in rows:
    result = row.get("result") or {}
    compact = {"id": row.get("id"), "ok": row.get("ok")}
    for field in fields[2:-1]:
        if field in result:
            compact[field] = result[field]
    if row.get("error"):
        compact["error"] = {"code": row["error"].get("code")}
    print(json.dumps(compact, sort_keys=True))'
CLAIM_ID="$(printf '%s\n' "$TOOL_JSON" | python3 -c 'import json,sys; rows=[json.loads(line) for line in sys.stdin if line.strip()]; approved=next(row for row in rows if row["id"]=="ingest-approved"); print(approved["result"]["created_claims"][0])')"
SOURCE_ID="$(printf '%s\n' "$TOOL_JSON" | python3 -c 'import json,sys; rows=[json.loads(line) for line in sys.stdin if line.strip()]; approved=next(row for row in rows if row["id"]=="ingest-approved"); print(approved["result"]["source_id"])')"
python3 "$ROOT/cli/akbp.py" --path "$KB" source verify --fail-on-issue
python3 "$ROOT/cli/akbp.py" --path "$KB" search "weekly evidence-backed"
python3 "$ROOT/cli/akbp.py" --path "$KB" context "prepare the next public alpha release"
python3 "$ROOT/cli/akbp.py" --path "$KB" supersede "$CLAIM_ID" \
  "AKBP public alpha releases should stay small, evidence-backed, and cadence-flexible until the protocol reaches 1.0." \
  --type decision \
  --evidence "$SOURCE_ID"
python3 "$ROOT/cli/akbp.py" --path "$KB" index --incremental
python3 "$ROOT/cli/akbp.py" --path "$KB" search "cadence-flexible evidence-backed"
python3 "$ROOT/cli/akbp.py" --path "$KB" audit --event supersede --limit 5
python3 "$ROOT/cli/akbp.py" --path "$KB" export --output "$BUNDLE"
python3 "$ROOT/cli/akbp.py" --path "$KB" export-check "$BUNDLE" --fail-on-issues
python3 "$ROOT/cli/akbp.py" --path "$KB" conformance --level 3

echo "AKBP quickstart demo passed"
echo "bundle=$BUNDLE"
