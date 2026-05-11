#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
TMP=${TMPDIR:-/tmp}/akbp-memory-ci-example-$$
KB="$TMP/kb"
BUNDLE="$TMP/akbp-bundle.json"
mkdir -p "$TMP"
cleanup() { rm -rf "$TMP"; }
trap cleanup EXIT
cd "$ROOT"

python3 cli/akbp.py --path "$KB" init >/dev/null
python3 cli/akbp.py --path "$KB" source add examples/memory-ci/review-note.md --type file --title "Memory CI review note" >/dev/null
python3 cli/akbp.py --path "$KB" remember "Memory CI should validate sources, conformance, export bundles, and imported JSONL proposals." --type workflow --confidence 0.88 --evidence examples/memory-ci/review-note.md >/dev/null

python3 cli/akbp.py --path "$KB" lint >/dev/null
python3 cli/akbp.py --path "$KB" source verify --fail-on-issue >/dev/null
python3 cli/akbp.py --path "$KB" conformance --level 2 >/dev/null
python3 cli/akbp.py --path "$KB" export --output "$BUNDLE" >/dev/null
python3 cli/akbp.py --path "$KB" export-check "$BUNDLE" --fail-on-issues >/dev/null
python3 cli/akbp.py --path "$KB" import-check examples/memory-ci/incoming.jsonl --fail-on-rejected >/dev/null
python3 cli/akbp.py --path "$KB" import-apply examples/memory-ci/incoming.jsonl --dry-run >/dev/null

echo "AKBP memory CI example passed"
