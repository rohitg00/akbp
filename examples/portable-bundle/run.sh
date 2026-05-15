#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

PRODUCER="$TMP/producer-kb"
CONSUMER="$TMP/consumer-kb"
BUNDLE="$TMP/akbp-bundle.json"
INCOMING="$TMP/incoming.jsonl"

echo "AKBP portable bundle example"

python3 "$ROOT/cli/akbp.py" --path "$PRODUCER" init >/dev/null
printf '%s\n' "Decision: portable memory handoffs must be manifest-checked before import." > "$PRODUCER/handoff-note.md"
SOURCE_ID="$(python3 "$ROOT/cli/akbp.py" --path "$PRODUCER" source add "$PRODUCER/handoff-note.md" --type file --title "Portable handoff note" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
python3 "$ROOT/cli/akbp.py" --path "$PRODUCER" remember "Decision: portable memory handoffs must be manifest-checked before import." --type decision --evidence "$SOURCE_ID" >/dev/null
python3 "$ROOT/cli/akbp.py" --path "$PRODUCER" index --incremental >/dev/null
python3 "$ROOT/cli/akbp.py" --path "$PRODUCER" export --output "$BUNDLE"
python3 "$ROOT/cli/akbp.py" --path "$PRODUCER" export-check "$BUNDLE" --fail-on-issues | python3 -c 'import json,sys; data=json.load(sys.stdin); assert data["ok"]; assert data["manifest_format"] == "akbp-portable-bundle"; print("bundle check ok")'

python3 "$ROOT/cli/akbp.py" --path "$CONSUMER" init >/dev/null
python3 - "$BUNDLE" "$INCOMING" <<'PY'
import json
import sys
from pathlib import Path

bundle = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
with Path(sys.argv[2]).open("w", encoding="utf-8") as out:
    for section in ("sources", "claims"):
        for item in bundle.get(section, []):
            item = dict(item)
            item["kind"] = "source" if section == "sources" else "claim"
            out.write(json.dumps(item, sort_keys=True) + "\n")
PY

python3 "$ROOT/cli/akbp.py" --path "$CONSUMER" import-check "$INCOMING" --fail-on-rejected | python3 -c 'import json,sys; data=json.load(sys.stdin); assert data["ok"]; assert data["accepted_count"] == 2; assert data["rejected_count"] == 0; print("import check ok")'
python3 "$ROOT/cli/akbp.py" --path "$CONSUMER" import-apply "$INCOMING" --dry-run | python3 -c 'import json,sys; data=json.load(sys.stdin); assert data["ok"]; assert data["dry_run"]; assert data["review_required"]; assert data["would_write"]["sources"]; assert data["would_write"]["claims"]; print("import preview ok")'
python3 "$ROOT/cli/akbp.py" --path "$CONSUMER" import-apply "$INCOMING" --approved | python3 -c 'import json,sys; data=json.load(sys.stdin); assert data["ok"]; assert data["applied"]; print("import apply ok")'
python3 "$ROOT/cli/akbp.py" --path "$CONSUMER" index --incremental >/dev/null
python3 "$ROOT/cli/akbp.py" --path "$CONSUMER" context "continue the portable memory handoff" | python3 -c 'import json,sys; data=json.load(sys.stdin); text=json.dumps(data); assert "manifest-checked" in text; print("consumer recall ok")'

echo "AKBP portable bundle example passed"
