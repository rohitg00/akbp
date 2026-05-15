#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

KB="$TMP/kb"
NOTE="$TMP/adoption-note.md"
DOCTOR_JSON="$TMP/doctor.json"
CONFIG_JSON="$TMP/client-config.json"

echo "AKBP adoption preflight example"

python3 "$ROOT/cli/akbp.py" --path "$KB" init >/dev/null

python3 "$ROOT/cli/akbp.py" --path "$KB" doctor --profile read-only > "$DOCTOR_JSON" || true
python3 - "$DOCTOR_JSON" <<'PY'
import json
import sys

doctor = json.loads(open(sys.argv[1], encoding="utf-8").read())
assert doctor["ok"], doctor
assert doctor["summary"]["errors"] == 0, doctor
assert doctor["adapter_readiness"]["startup_context_ready"], doctor
assert not doctor["adapter_readiness"]["read_only_ready"], doctor
assert not doctor["adapter_readiness"]["reviewed_write_ready"], doctor
assert doctor["adapter_readiness"]["blocking_checks"] == [], doctor
assert doctor["security_posture"]["write_boundary"] == "dry_run_preview_then_approved_apply", doctor
print("fresh KB starts with read-only trust boundary ok")
PY

printf '%s\n' "Adoption preflight should prove cited startup context before enabling memory writes." > "$NOTE"
python3 "$ROOT/cli/akbp.py" --path "$KB" source add "$NOTE" --type file --title "Adoption preflight note" >/dev/null
python3 "$ROOT/cli/akbp.py" --path "$KB" remember "Adapters should prove cited startup context before enabling write-capable memory." --type workflow --confidence 0.93 --evidence "$NOTE" >/dev/null
python3 "$ROOT/cli/akbp.py" --path "$KB" index --incremental >/dev/null

python3 "$ROOT/tool-server/akbp_tool_server.py" <<JSONL | python3 -c '
import json
import sys

rows = [json.loads(line) for line in sys.stdin if line.strip()]
by_id = {row["id"]: row for row in rows}

doctor = by_id["doctor"]
assert doctor["ok"], doctor
assert doctor["result"]["adapter_readiness"]["startup_context_ready"], doctor
assert doctor["result"]["adapter_readiness"]["read_only_ready"], doctor
assert doctor["result"]["summary"]["errors"] == 0, doctor

start = by_id["session-start"]
assert start["ok"], start
items = start["result"]["context"]["items"]
assert items, start
assert any(item.get("citations") for item in items), start
assert "startup context" in " ".join(item.get("summary", "") for item in items), start
print("cited startup context becomes ready ok")

blocked = by_id["write-blocked"]
assert not blocked["ok"], blocked
assert blocked["error"]["code"] == "approval_required", blocked
assert blocked["error"]["details"]["review_required"], blocked
print("unapproved write rejection ok")
'
{"id":"doctor","method":"akbp.doctor","path":"$KB"}
{"id":"session-start","method":"akbp.session.start","path":"$KB","params":{"task":"adopt AKBP with cited startup context","limit":5}}
{"id":"write-blocked","method":"akbp.remember","path":"$KB","params":{"text":"Unapproved adoption writes must remain blocked.","type":"workflow"}}
JSONL

python3 "$ROOT/cli/akbp.py" --path "$KB" client-config --profile read-only --portable > "$CONFIG_JSON"
python3 - "$CONFIG_JSON" <<'PY'
import json
import sys

config = json.loads(open(sys.argv[1], encoding="utf-8").read())
assert config["knowledge_base"]["path"] == "<AKBP_KB_PATH>", config
assert config["knowledge_base"]["portable_template"], config
assert config["tool_protocol_bridge"]["mode"] == "read_only", config
assert "akbp.remember" in config["tool_protocol_bridge"]["blocked_write_methods"], config
assert config["safety"]["write_policy"] == "no_writes", config
assert config["runtime_requirements"]["local_first"], config
assert not config["runtime_requirements"]["network_required"], config
print("portable client config hides local paths ok")
PY

echo "AKBP adoption preflight example passed"
