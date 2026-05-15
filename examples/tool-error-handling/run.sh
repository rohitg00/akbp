#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
KB="${1:-$(mktemp -d)/akbp-tool-error-kb}"

echo "AKBP tool error handling"
echo "kb=$KB"

python3 "$ROOT/cli/akbp.py" --path "$KB" init >/dev/null

RESPONSES="$(printf '%s\n' \
  '{"id":"caps","method":"akbp.capabilities","path":"'"$KB"'","params":{"client":"tool-error-handling-example","requires":["structured_errors","method_param_schemas","approval_required_errors"]}}' \
  '{"id":"broken","method":"akbp.search"' \
  '{"id":"bad-envelope","method":"akbp.search","path":"'"$KB"'","params":{"query":"release"},"unexpected":true}' \
  '{"id":"unknown","method":"akbp.nope","path":"'"$KB"'","params":{}}' \
  '{"id":"bad-limit","method":"akbp.search","path":"'"$KB"'","params":{"query":"release","limit":0}}' \
  '{"id":"remember-preview","method":"akbp.remember","path":"'"$KB"'","dry_run":true,"params":{"text":"Decision: keep reviewed writes explicit.","type":"decision"}}' \
  '{"id":"remember-blocked","method":"akbp.remember","path":"'"$KB"'","params":{"text":"Decision: keep reviewed writes explicit.","type":"decision"}}' \
  '{"id":"remember-approved","method":"akbp.remember","path":"'"$KB"'","approved":true,"params":{"text":"Decision: keep reviewed writes explicit.","type":"decision"}}' \
  '{"id":"missing-cite","method":"akbp.cite","path":"'"$KB"'","params":{"claim_id":"claim_missing"}}' \
  | python3 "$ROOT/tool-server/akbp_tool_server.py")"

RESPONSES="$RESPONSES" python3 - <<'PY'
import json
import os
import sys

rows = [json.loads(line) for line in os.environ["RESPONSES"].splitlines() if line.strip()]
by_id = {row["id"]: row for row in rows}
by_code = {row["error"]["code"]: row for row in rows if row.get("error")}

caps = by_id["caps"]
assert caps["ok"], caps
features = caps["result"]["features"]
assert features["structured_errors"], caps
assert features["method_param_schemas"], caps
assert features["approval_required_errors"], caps

assert by_code["invalid_json"]["id"] is None, by_code["invalid_json"]
assert by_id["bad-envelope"]["error"]["code"] == "invalid_request", by_id["bad-envelope"]
assert by_id["unknown"]["error"]["code"] == "unknown_method", by_id["unknown"]
assert "akbp.search" in by_id["unknown"]["error"]["details"]["available_methods"], by_id["unknown"]

bad_limit = by_id["bad-limit"]
assert bad_limit["error"]["code"] == "invalid_params", bad_limit
assert bad_limit["error"]["details"]["params_schema"].endswith("#/$defs/akbp.search.params"), bad_limit
assert any("limit must be between 1 and 100" in item for item in bad_limit["error"]["details"]["type_errors"]), bad_limit

preview = by_id["remember-preview"]
assert preview["ok"], preview
assert preview["result"]["dry_run"], preview
assert preview["result"]["review_required"], preview
assert "apply_instruction" in preview["result"], preview

blocked = by_id["remember-blocked"]
assert blocked["error"]["code"] == "approval_required", blocked
assert blocked["error"]["details"]["review_required"], blocked

approved = by_id["remember-approved"]
assert approved["ok"], approved
assert approved["result"]["id"].startswith("claim_"), approved

missing_cite = by_id["missing-cite"]
assert missing_cite["error"]["code"] == "cli_error", missing_cite
assert missing_cite["error"]["details"]["exit_code"] != 0, missing_cite
assert "redacted" in missing_cite["error"]["details"], missing_cite

actions = {
    "invalid_json": "repair JSON serialization",
    "invalid_request": "repair request envelope",
    "unknown_method": "refresh capabilities and disable unavailable flow",
    "invalid_params": "repair params from advertised schema",
    "approval_required": "stop apply path until reviewed approval",
    "cli_error": "surface redacted CLI failure",
}
for code, action in actions.items():
    assert code in by_code, code
    assert action, action

print("structured error handling ok")
PY

test "$(python3 - <<'PY' "$KB/claims/claims.jsonl"
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
print(len(rows))
PY
)" = "1"

echo "AKBP tool error handling passed"
