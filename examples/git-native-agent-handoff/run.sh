#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
TMP=${TMPDIR:-/tmp}/akbp-git-native-handoff-$$
KB="$TMP/kb"
mkdir -p "$TMP"
cleanup() { rm -rf "$TMP"; }
trap cleanup EXIT
cd "$ROOT"

python3 cli/akbp.py --path "$KB" init >/dev/null
python3 cli/akbp.py --path "$KB" source add adapters/git-native-agent/README.md --type file --title "Git-native adapter README" >/dev/null
python3 cli/akbp.py --path "$KB" remember "Git-native agents should retrieve cited AKBP context before planning substantial repository work." --type workflow --confidence 0.9 --evidence adapters/git-native-agent/README.md --entity git-native-agent >/dev/null
python3 cli/akbp.py --path "$KB" remember "Git-native agents must preview durable memory writes with dry_run before applying them with approved:true." --type workflow --confidence 0.92 --evidence adapters/git-native-agent/README.md --entity review-gated-writes >/dev/null
python3 cli/akbp.py --path "$KB" index >/dev/null

REQUESTS=$(cat <<JSONL
{"id":"caps","method":"akbp.capabilities","path":"$KB"}
{"id":"start","method":"akbp.session.start","path":"$KB","params":{"task":"continue git-native adapter work with safe memory writes","limit":5}}
{"id":"end-preview","method":"akbp.session.end","path":"$KB","dry_run":true,"params":{"transcript":"examples/git-native-agent-handoff/session-summary.md","apply":true}}
{"id":"end-blocked","method":"akbp.session.end","path":"$KB","params":{"transcript":"examples/git-native-agent-handoff/session-summary.md","apply":true}}
{"id":"end-approved","method":"akbp.session.end","path":"$KB","approved":true,"params":{"transcript":"examples/git-native-agent-handoff/session-summary.md","apply":true}}
{"id":"index","method":"akbp.index","path":"$KB","approved":true,"params":{"incremental":true}}
JSONL
)

RESPONSES=$(printf '%s\n' "$REQUESTS" | python3 tool-server/akbp_tool_server.py)
python3 -c '
import json, sys
rows = [json.loads(line) for line in sys.stdin if line.strip()]
by_id = {row["id"]: row for row in rows}
assert by_id["caps"]["result"]["features"]["method_param_schemas"], by_id["caps"]
assert "akbp.session.start" in by_id["caps"]["result"]["methods"], by_id["caps"]
items = by_id["start"]["result"]["context"]["items"]
assert any("Git-native agents should retrieve cited AKBP context" in item.get("summary", "") for item in items), by_id["start"]
assert by_id["end-preview"]["result"]["review_required"], by_id["end-preview"]
assert by_id["end-blocked"]["error"]["code"] == "approval_required", by_id["end-blocked"]
assert by_id["end-approved"]["ok"], by_id["end-approved"]
assert by_id["index"]["result"]["ok"], by_id["index"]
' <<<"$RESPONSES"

echo "AKBP git-native handoff example passed"
