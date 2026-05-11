#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
TMP=${TMPDIR:-/tmp}/akbp-multi-agent-consistency-$$
KB="$TMP/kb"
mkdir -p "$TMP"

cleanup() {
  rm -rf "$TMP"
}
trap cleanup EXIT

cd "$ROOT"

echo "== Agent A initializes shared AKBP knowledge =="
python3 cli/akbp.py --path "$KB" init >/dev/null
python3 cli/akbp.py --path "$KB" source add examples/multi-agent-consistency-demo/agent-a-notes.md --type file --title "Agent A notes" >/dev/null
AGENT_A_CLAIM_JSON=$(python3 cli/akbp.py --path "$KB" remember "Decision: keep public alpha updates small and reviewable." --type decision --confidence 0.82 --evidence examples/multi-agent-consistency-demo/agent-a-notes.md)
AGENT_A_CLAIM=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])' <<<"$AGENT_A_CLAIM_JSON")
echo "Agent A claim: $AGENT_A_CLAIM"

echo "== Agent B retrieves cited context before changing direction =="
python3 cli/akbp.py --path "$KB" index >/dev/null
python3 cli/akbp.py --path "$KB" context "public alpha release plan" --limit 3

echo "== Agent B supersedes with a validated workflow detail =="
python3 cli/akbp.py --path "$KB" source add examples/multi-agent-consistency-demo/agent-b-notes.md --type file --title "Agent B notes" >/dev/null
AGENT_B_CLAIM_JSON=$(python3 cli/akbp.py --path "$KB" supersede "$AGENT_A_CLAIM" "Decision: keep public alpha updates small, reviewable, and backed by a validation result before apply." --type decision --confidence 0.9 --evidence examples/multi-agent-consistency-demo/agent-b-notes.md)
AGENT_B_CLAIM=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])' <<<"$AGENT_B_CLAIM_JSON")
echo "Agent B claim: $AGENT_B_CLAIM"

echo "== Final consistency check =="
python3 cli/akbp.py --path "$KB" conformance --level 3
python3 cli/akbp.py --path "$KB" search "validation result" --limit 5

echo "AKBP multi-agent consistency demo passed"
