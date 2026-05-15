#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
KB="${1:-$(mktemp -d)/akbp-demo-kb}"
NOTE="$ROOT/examples/quickstart-demo/session-note.md"
BUNDLE="$KB/export.json"

echo "AKBP quickstart demo"
echo "kb=$KB"

python3 "$ROOT/cli/akbp.py" --path "$KB" init
python3 "$ROOT/cli/akbp.py" --path "$KB" source add "$NOTE" --type file --title "Demo session note"
INGEST_JSON="$(python3 "$ROOT/cli/akbp.py" --path "$KB" ingest "$NOTE" \
  --claim "AKBP public alpha releases should stay small, weekly, and evidence-backed until the protocol reaches 1.0." \
  --claim-type decision)"
printf '%s\n' "$INGEST_JSON"
CLAIM_ID="$(printf '%s\n' "$INGEST_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["created_claims"][0])')"
SOURCE_ID="$(printf '%s\n' "$INGEST_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["source_id"])')"
python3 "$ROOT/cli/akbp.py" --path "$KB" source verify --fail-on-issue
python3 "$ROOT/cli/akbp.py" --path "$KB" index --incremental
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
