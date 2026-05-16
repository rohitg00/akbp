#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

KB="$TMP/kb"
NOTE="$TMP/adoption-note.md"
DOCTOR_JSON="$TMP/doctor.json"
CONFIG_JSON="$TMP/client-config.json"
DISCOVER_JSON="$TMP/discover.json"

echo "AKBP adoption preflight example"

python3 "$ROOT/cli/akbp.py" --path "$KB" init >/dev/null

mkdir -p "$KB/app/src"
python3 "$ROOT/cli/akbp.py" --path "$KB/app/src" discover > "$DISCOVER_JSON"
python3 - "$DISCOVER_JSON" "$KB" <<'PY'
import json
import os
import sys

discover = json.loads(open(sys.argv[1], encoding="utf-8").read())
kb = os.path.realpath(sys.argv[2])

assert discover["found"], discover
assert os.path.realpath(discover["path"]) == kb, discover
assert os.path.realpath(discover["trust_boundary"]["read_path"]) == kb, discover
assert discover["positioning"]["not_a_hidden_memory_store"], discover

profiles = discover["profile_selection"]
assert profiles["safe_default"] == "read_only", profiles
assert [profile["profile"] for profile in profiles["profiles"]] == [
    "startup_context",
    "read_only",
    "reviewed_write",
], profiles
assert "keep the integration read-only" in profiles["fallback"], profiles

proof = discover["ten_minute_proof"]
assert proof["format"] == "akbp-ten-minute-proof-v1", proof
assert not proof["setup_claims"]["requires_docker"], proof
assert not proof["setup_claims"]["requires_cloud_account"], proof
assert not proof["setup_claims"]["requires_secrets"], proof
proof_step_names = [step["name"] for step in proof["proof_steps"]]
required_proof_steps = [
    "create_visible_artifacts",
    "check_readiness",
    "retrieve_cited_context",
    "verify_inherited_sources",
    "preview_reviewed_write",
    "block_unapproved_apply",
    "validate_adapter_response_contract",
    "export_portable_bundle",
]
for required_step in required_proof_steps:
    assert required_step in proof_step_names, proof
assert [proof_step_names.index(step) for step in required_proof_steps] == sorted(
    proof_step_names.index(step) for step in required_proof_steps
), proof

harness = discover["first_run_proof"]["recommended_harness"]
assert harness["command"] == "./examples/structured-output-harness/run.sh", harness
assert "keep the integration read-only" in harness["stop_policy"], harness

prompt = discover["adapter_prompt_contract"]
assert prompt["format"] == "akbp-adapter-prompt-contract-v1", prompt
assert any("ok field and error.code" in rule for rule in prompt["system_rules"]), prompt
print("nested discovery profile proof ok")
PY

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
python3 "$ROOT/cli/akbp.py" --path "$KB" context "adopt AKBP with cited startup context" --max-chars 4000 --min-items 1 --require-citations >/dev/null
echo "CLI startup context quality gate ok"

python3 "$ROOT/tool-server/akbp_tool_server.py" <<JSONL | python3 -c '
import json
import sys

rows = [json.loads(line) for line in sys.stdin if line.strip()]
by_id = {row["id"]: row for row in rows}

caps = by_id["caps"]
assert caps["ok"], caps
assert caps["result"]["negotiation"]["satisfied"], caps
assert caps["result"]["features"]["approval_required_errors"], caps
assert "read_only" in caps["result"]["negotiation"]["supported_profiles"], caps

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
print("capability negotiation read-only profile ok")

blocked = by_id["write-blocked"]
assert not blocked["ok"], blocked
assert blocked["error"]["code"] == "approval_required", blocked
assert blocked["error"]["details"]["review_required"], blocked
print("unapproved write rejection ok")
'
{"id":"caps","method":"akbp.capabilities","path":"$KB","params":{"client":"adoption-preflight","requires":["method_param_schemas","capability_negotiation","approval_required_errors"],"requires_profiles":["read_only"]}}
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
assert config["response_contract"]["envelope"]["required"] == ["id", "ok", "result", "error"], config
assert config["response_contract"]["error_actions"]["approval_required"]["adapter_action"].startswith("stop"), config
assert config["response_contract"]["error_actions"]["approval_required"]["write_policy"] == "approval must happen outside the model-generated tool call", config

probe = config["memory_landscape_fit"]["local_first_adoption_probe"]
assert probe["format"] == "akbp-local-first-adoption-probe-v1", probe
assert probe["run_before_positioning_claims"], probe
assert "akbp discover" in probe["commands"], probe
assert "akbp doctor --profile read-only" in probe["commands"], probe
assert "akbp client-config --profile read-only" in probe["commands"], probe
assert "./examples/structured-output-harness/run.sh" in probe["commands"], probe
assert any("export-check" in command for command in probe["commands"]), probe
assert any("approval_required" in item for item in probe["must_prove"]), probe
assert any("opaque sidecar database" in item for item in probe["fail_closed_when"]), probe
assert "read-only startup context" in probe["fallback"], probe
print("portable client config hides local paths ok")
print("response contract approval stop action ok")
print("local-first adoption probe contract ok")
PY

echo "AKBP adoption preflight example passed"
