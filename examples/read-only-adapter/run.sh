#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

KB="$TMP/kb"
IMPORT="$TMP/incoming.jsonl"

echo "AKBP read-only adapter example"

python3 "$ROOT/cli/akbp.py" --path "$KB" init >/dev/null
python3 "$ROOT/cli/akbp.py" --path "$KB" source add "$ROOT/README.md" --type file --title "AKBP README" >/dev/null
python3 "$ROOT/cli/akbp.py" --path "$KB" remember "Adapters should retrieve cited AKBP context before planning substantial work." --type workflow --confidence 0.85 --evidence "$ROOT/README.md" >/dev/null
python3 "$ROOT/cli/akbp.py" --path "$KB" index --incremental >/dev/null

cat > "$IMPORT" <<'JSONL'
{"kind":"source","id":"source_read_only_adapter_import","type":"note","locator":"read-only-adapter.md","title":"Read-only adapter note"}
JSONL

python3 "$ROOT/tool-server/akbp_tool_server.py" <<JSONL | python3 -c '
import json, sys

rows = [json.loads(line) for line in sys.stdin if line.strip()]
by_id = {row["id"]: row for row in rows}

caps = by_id["caps"]["result"]
read_only = set(caps["profiles"]["read_only"])
assert "akbp.search" in read_only
assert "akbp.import_check" in read_only
assert "akbp.session.start" in read_only
assert "akbp.remember" not in read_only
assert "akbp.import_apply" not in read_only
for method in read_only:
    assert not caps["methods"][method]["write"], method

start = by_id["start"]["result"]
assert start["context"]["items"], start
assert "Adapters should retrieve cited AKBP context" in json.dumps(start)

search = by_id["search"]["result"]
assert search["results"], search

check = by_id["import-check"]["result"]
assert check["ok"], check
assert check["accepted_count"] == 1, check

blocked = {
    "ok": False,
    "error": {
        "code": "adapter_read_only_block",
        "message": "adapter blocks akbp.remember because it is not in result.profiles.read_only",
    },
}
assert blocked["ok"] is False
assert blocked["error"]["code"] == "adapter_read_only_block"

print("read-only allowlist ok")
'
{"id":"caps","method":"akbp.capabilities","path":"$KB","params":{"client":"read-only-adapter-example","requires":["method_param_schemas","capability_negotiation"]}}
{"id":"start","method":"akbp.session.start","path":"$KB","params":{"task":"plan adapter integration work","limit":5}}
{"id":"search","method":"akbp.search","path":"$KB","params":{"query":"adapter context retrieval","limit":5}}
{"id":"import-check","method":"akbp.import_check","path":"$KB","params":{"file":"$IMPORT","fail_on_rejected":true}}
JSONL

python3 "$ROOT/cli/akbp.py" --path "$KB" status | python3 -c 'import json,sys; data=json.load(sys.stdin); assert data["counts"]["claims"] == 1; print("no read-only write occurred")'

echo "AKBP read-only adapter example passed"
