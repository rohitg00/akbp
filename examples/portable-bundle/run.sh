#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

PRODUCER="$TMP/producer-kb"
CONSUMER="$TMP/consumer-kb"
BUNDLE="$TMP/akbp-bundle.json"

echo "AKBP portable bundle example"

python3 "$ROOT/cli/akbp.py" --path "$PRODUCER" init >/dev/null
printf '%s\n' "Decision: portable memory handoffs must be manifest-checked before import." > "$PRODUCER/handoff-note.md"
SOURCE_ID="$(python3 "$ROOT/cli/akbp.py" --path "$PRODUCER" source add "$PRODUCER/handoff-note.md" --type file --title "Portable handoff note" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
python3 "$ROOT/cli/akbp.py" --path "$PRODUCER" remember "Decision: portable memory handoffs must be manifest-checked before import." --type decision --evidence "$SOURCE_ID" >/dev/null
python3 "$ROOT/cli/akbp.py" --path "$PRODUCER" index --incremental >/dev/null
python3 "$ROOT/cli/akbp.py" --path "$PRODUCER" export --output "$BUNDLE"
python3 "$ROOT/cli/akbp.py" --path "$PRODUCER" export-check "$BUNDLE" --fail-on-issues | python3 -c 'import json,sys; data=json.load(sys.stdin); assert data["ok"]; assert data["manifest_format"] == "akbp-portable-bundle"; print("bundle check ok")'

python3 "$ROOT/cli/akbp.py" --path "$CONSUMER" init >/dev/null
python3 "$ROOT/cli/akbp.py" --path "$CONSUMER" import-check "$BUNDLE" --fail-on-rejected | python3 -c 'import json,sys; data=json.load(sys.stdin); assert data["ok"]; assert data["accepted_count"] == 2; assert data["rejected_count"] == 0; assert data["review"]["ready_for_reviewed_apply"]; assert data["review"]["claims_without_evidence"] == []; print("import check ok")'
python3 "$ROOT/cli/akbp.py" --path "$CONSUMER" import-apply "$BUNDLE" --dry-run | python3 -c 'import json,sys; data=json.load(sys.stdin); assert data["ok"]; assert data["dry_run"]; assert data["review_required"]; assert data["would_write"]["sources"]; assert data["would_write"]["claims"]; assert data["review"]["ready_for_reviewed_apply"]; print("import preview ok")'
python3 "$ROOT/cli/akbp.py" --path "$CONSUMER" import-apply "$BUNDLE" --approved | python3 -c 'import json,sys; data=json.load(sys.stdin); assert data["ok"]; assert data["applied"]; print("import apply ok")'
python3 "$ROOT/cli/akbp.py" --path "$CONSUMER" index --incremental >/dev/null
python3 "$ROOT/cli/akbp.py" --path "$CONSUMER" context "continue the portable memory handoff" | python3 -c 'import json,sys; data=json.load(sys.stdin); text=json.dumps(data); assert "manifest-checked" in text; print("consumer recall ok")'

echo "AKBP portable bundle example passed"
