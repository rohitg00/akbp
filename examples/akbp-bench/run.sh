#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
TMP=${TMPDIR:-/tmp}/akbp-bench-example-$$
KB="$TMP/kb"
BUNDLE="$TMP/bundle.json"
mkdir -p "$TMP"
cleanup() { rm -rf "$TMP"; }
trap cleanup EXIT
cd "$ROOT"

pass() { printf 'PASS %s\n' "$1"; }

python3 cli/akbp.py --path "$KB" init >/dev/null
python3 cli/akbp.py --path "$KB" source add examples/akbp-bench/release-source.md --type file --title "Public alpha release note" >/dev/null
CLAIM_JSON=$(python3 cli/akbp.py --path "$KB" remember "Decision: public alpha changes stay small, reviewed, and evidence-backed." --type decision --confidence 0.84 --evidence examples/akbp-bench/release-source.md)
CLAIM_ID=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])' <<<"$CLAIM_JSON")
pass "record cited claim"

python3 cli/akbp.py --path "$KB" index >/dev/null
CONTEXT_JSON=$(python3 cli/akbp.py --path "$KB" context "public alpha release rule" --limit 3)
python3 -c 'import json,sys; data=json.load(sys.stdin); assert data["items"], data; assert any(item.get("citations") for item in data["items"]), data' <<<"$CONTEXT_JSON"
pass "retrieve cited context"

python3 cli/akbp.py --path "$KB" source add examples/akbp-bench/release-update.md --type file --title "Public alpha release update" >/dev/null
python3 cli/akbp.py --path "$KB" supersede "$CLAIM_ID" "Decision: public alpha changes stay small, reviewed, and backed by validation output before apply." --type decision --confidence 0.9 --evidence examples/akbp-bench/release-update.md >/dev/null
python3 cli/akbp.py --path "$KB" conformance --level 3 >/dev/null
pass "preserve lifecycle relation"

python3 cli/akbp.py --path "$KB" export --output "$BUNDLE" >/dev/null
python3 cli/akbp.py --path "$KB" export-check "$BUNDLE" --fail-on-issues >/dev/null
pass "export portable bundle"

cat <<'SCORECARD'

AKBP bench scorecard
- cited write: pass
- cited retrieval: pass
- supersession lifecycle: pass
- portable export check: pass
- level 3 conformance: pass

AKBP bench example passed
SCORECARD
