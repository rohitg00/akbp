#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

KB="$TMP/kb"
UPDATES="$ROOT/examples/rich-context-artifact/updates.jsonl"
EXPORT="$TMP/export.json"

echo "AKBP rich context artifact gate"

python3 "$ROOT/cli/akbp.py" --path "$KB" init >/dev/null

python3 "$ROOT/cli/akbp.py" --path "$KB" import-check "$UPDATES" --fail-on-rejected |
  python3 -c '
import json
import sys

payload = json.load(sys.stdin)
assert payload["ok"], payload
assert payload["accepted_count"] == 3, payload
assert payload["rejected_count"] == 0, payload
assert payload["review"]["source_count"] == 1, payload
assert payload["review"]["claim_count"] == 2, payload
print("import check ok")
'

python3 "$ROOT/cli/akbp.py" --path "$KB" import-apply "$UPDATES" --dry-run |
  python3 -c '
import json
import sys

payload = json.load(sys.stdin)
assert payload["ok"], payload
assert payload["dry_run"] is True, payload
assert payload["applied"] is False, payload
assert payload["review_required"] is True, payload
assert "source_rich_context_handoff_note" in payload["would_write"]["sources"], payload
assert "claim_jsonl_proposals_are_write_path" in payload["would_write"]["claims"], payload
print("dry-run import preview ok")
'

python3 "$ROOT/cli/akbp.py" --path "$KB" import-apply "$UPDATES" --approved |
  python3 -c '
import json
import sys

payload = json.load(sys.stdin)
assert payload["ok"], payload
assert payload["applied"] is True, payload
assert payload["accepted_count"] == 3, payload
print("approved import apply ok")
'

python3 "$ROOT/cli/akbp.py" --path "$KB" source verify --fail-on-issue |
  python3 -c '
import json
import sys

payload = json.load(sys.stdin)
assert payload["ok"], payload
assert payload["counts"]["verified"] == 1, payload
assert payload["counts"]["changed"] == 0, payload
assert payload["counts"]["missing"] == 0, payload
assert payload["counts"]["unchecked"] == 0, payload
print("source verification ok")
'

python3 "$ROOT/cli/akbp.py" --path "$KB" index --incremental >/dev/null
python3 "$ROOT/cli/akbp.py" --path "$KB" context "rich review artifact handoff" --require-citations |
  python3 -c '
import json
import sys

payload = json.load(sys.stdin)
assert payload["quality"]["ok"], payload
claim_items = [item for item in payload["items"] if item["type"] == "claim"]
assert len(claim_items) >= 2, payload
assert all(item["citations"] for item in claim_items), payload
print("cited recall ok")
'

python3 "$ROOT/cli/akbp.py" --path "$KB" export --output "$EXPORT" >/dev/null
python3 "$ROOT/cli/akbp.py" --path "$KB" export-check "$EXPORT" --fail-on-issues |
  python3 -c '
import json
import sys

payload = json.load(sys.stdin)
assert payload["ok"], payload
assert payload["issues"] == [], payload
print("export check ok")
'

echo "AKBP rich context artifact gate passed"
