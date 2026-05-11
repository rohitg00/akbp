#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
TMP=${TMPDIR:-/tmp}/akbp-repo-memory-demo-$$
KB="$TMP/kb"
mkdir -p "$TMP"
cleanup() { rm -rf "$TMP"; }
trap cleanup EXIT
cd "$ROOT"

python3 cli/akbp.py --path "$KB" init >/dev/null
python3 cli/akbp.py --path "$KB" source add examples/repo-memory-demo/fixtures/issue-17.md --type issue --title "Issue 17" >/dev/null
python3 cli/akbp.py --path "$KB" source add examples/repo-memory-demo/fixtures/pr-42.md --type file --title "PR 42" >/dev/null
python3 cli/akbp.py --path "$KB" source add examples/repo-memory-demo/fixtures/release-note.md --type file --title "Release note" >/dev/null

python3 cli/akbp.py --path "$KB" remember "Importing JSONL memory bundles must validate records before durable apply." --type decision --confidence 0.86 --evidence examples/repo-memory-demo/fixtures/issue-17.md >/dev/null
python3 cli/akbp.py --path "$KB" remember "Import apply should start with a dry-run preview of accepted source and claim ids." --type workflow --confidence 0.9 --evidence examples/repo-memory-demo/fixtures/pr-42.md >/dev/null
python3 cli/akbp.py --path "$KB" remember "Adapters should run import-check, inspect dry-run output, then apply only with explicit approval." --type workflow --confidence 0.92 --evidence examples/repo-memory-demo/fixtures/release-note.md >/dev/null

python3 cli/akbp.py --path "$KB" index >/dev/null
CONTEXT=$(python3 cli/akbp.py --path "$KB" context "continue import workflow adapter work" --limit 5)
python3 -c 'import json,sys; data=json.load(sys.stdin); assert len(data["items"]) >= 2, data; assert any(item.get("citations") for item in data["items"]), data' <<<"$CONTEXT"

echo "Later-session context:"
printf '%s\n' "$CONTEXT"

echo "AKBP repo memory demo passed"
