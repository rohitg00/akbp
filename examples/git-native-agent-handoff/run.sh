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
BRANCH_SOURCE_ID=$(python3 cli/akbp.py --path "$KB" source add examples/git-native-agent-handoff/session-summary.md --type transcript --title "Git-native branch handoff summary" | python3 -c 'import json, sys; print(json.load(sys.stdin)["id"])')
python3 cli/akbp.py --path "$KB" remember "Git-native agents should retrieve cited AKBP context before planning substantial repository work." --type workflow --confidence 0.9 --evidence adapters/git-native-agent/README.md --entity git-native-agent >/dev/null
python3 cli/akbp.py --path "$KB" remember "Git-native agents must preview durable memory writes with dry_run before applying them with approved:true." --type workflow --confidence 0.92 --evidence adapters/git-native-agent/README.md --entity review-gated-writes >/dev/null
BRANCH_CLAIM_ID=$(python3 cli/akbp.py --path "$KB" remember "Branch-scoped git-native handoffs must preserve branch name feature/adapter-review, commit SHA or dirty-worktree marker, and cited source ids before another checkout reuses the memory." --type workflow --confidence 0.91 --evidence "$BRANCH_SOURCE_ID" --entity branch-scoped-handoff | python3 -c 'import json, sys; print(json.load(sys.stdin)["id"])')
python3 cli/akbp.py --path "$KB" index >/dev/null

REQUESTS=$(cat <<JSONL
{"id":"caps","method":"akbp.capabilities","path":"$KB"}
{"id":"start","method":"akbp.session.start","path":"$KB","params":{"task":"continue git-native adapter work from branch feature/adapter-review with safe memory writes","limit":5}}
{"id":"context-branch-scope","method":"akbp.context","path":"$KB","params":{"task":"reuse branch-scoped handoff memory on another checkout with citations","limit":5,"require_citations":true}}
{"id":"cite-branch-scope","method":"akbp.cite","path":"$KB","params":{"claim_id":"$BRANCH_CLAIM_ID"}}
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
branch_items = by_id["context-branch-scope"]["result"]["items"]
assert any("feature/adapter-review" in item.get("summary", "") for item in branch_items), by_id["context-branch-scope"]
assert by_id["cite-branch-scope"]["result"]["claim_id"], by_id["cite-branch-scope"]
assert by_id["cite-branch-scope"]["result"]["evidence"], by_id["cite-branch-scope"]
assert by_id["end-preview"]["result"]["review_required"], by_id["end-preview"]
assert by_id["end-blocked"]["error"]["code"] == "approval_required", by_id["end-blocked"]
assert by_id["end-approved"]["ok"], by_id["end-approved"]
assert by_id["index"]["result"]["ok"], by_id["index"]
' <<<"$RESPONSES"

echo "AKBP git-native handoff example passed"
