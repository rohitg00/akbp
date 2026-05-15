#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

KB="$TMP/kb"

echo "AKBP session-start harness example"

python3 "$ROOT/cli/akbp.py" --path "$KB" init >/dev/null
python3 "$ROOT/cli/akbp.py" --path "$KB" source add "$ROOT/README.md" --type file --title "AKBP README" >/dev/null
python3 "$ROOT/cli/akbp.py" --path "$KB" remember "Adapters must retrieve cited AKBP context at session start before planning integration work." --type workflow --confidence 0.9 --evidence "$ROOT/README.md" >/dev/null
python3 "$ROOT/cli/akbp.py" --path "$KB" index --incremental >/dev/null

python3 "$ROOT/tool-server/akbp_tool_server.py" <<JSONL | python3 -c '
import json, sys

rows = [json.loads(line) for line in sys.stdin if line.strip()]
by_id = {row["id"]: row for row in rows}

caps = by_id["caps"]
assert caps["ok"], caps
negotiation = caps["result"]["negotiation"]
assert negotiation["satisfied"], negotiation
assert "read_only" in negotiation["supported_profiles"], negotiation
assert "startup_context" in negotiation["supported_profiles"], negotiation
assert caps["result"]["features"]["method_param_schemas"], caps

doctor = by_id["doctor"]
assert doctor["ok"], doctor
assert doctor["result"]["ready_for_adapter"], doctor
assert doctor["result"]["summary"]["errors"] == 0, doctor

start = by_id["start"]
assert start["ok"], start
result = start["result"]
assert result["session_id"].startswith("adapter_session_"), result
assert result["task"] == "plan adapter integration work", result
context = result["context"]
assert context["items"], context
assert isinstance(context["warnings"], list), context

first = context["items"][0]
assert first["type"] == "claim", first
assert first["citations"], first
assert "Adapters must retrieve cited AKBP context" in first["summary"], first

print("session-start harness ok")
'
{"id":"caps","method":"akbp.capabilities","path":"$KB","params":{"client":"session-start-harness","requires":["method_param_schemas","capability_negotiation"],"requires_profiles":["read_only","startup_context"]}}
{"id":"doctor","method":"akbp.doctor","path":"$KB"}
{"id":"start","method":"akbp.session.start","path":"$KB","params":{"task":"plan adapter integration work","limit":5}}
JSONL

echo "AKBP session-start harness example passed"
