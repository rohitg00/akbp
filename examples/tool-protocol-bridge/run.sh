#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

KB="$TMP/kb"
NOTE="$TMP/bridge-note.md"
CONFIG="$TMP/bridge-config.json"

echo "AKBP tool-protocol bridge preflight"

python3 "$ROOT/cli/akbp.py" --path "$KB" init >/dev/null
printf '%s\n' "Tool-protocol bridges should start read-only, preserve AKBP response fields, and require a separate reviewed-write surface before applying durable memory." > "$NOTE"
python3 "$ROOT/cli/akbp.py" --path "$KB" source add "$NOTE" --type file --title "Tool bridge preflight note" >/dev/null
python3 "$ROOT/cli/akbp.py" --path "$KB" remember "Tool-protocol bridges should expose AKBP read-only wrappers before enabling reviewed writes." --type workflow --confidence 0.91 --evidence "$NOTE" >/dev/null
python3 "$ROOT/cli/akbp.py" --path "$KB" index --incremental >/dev/null
python3 "$ROOT/cli/akbp.py" --path "$KB" client-config --name tool-protocol-bridge --profile read-only > "$CONFIG"

python3 - "$CONFIG" <<'PY'
import json
import sys

config = json.loads(open(sys.argv[1], encoding="utf-8").read())
bridge = config["tool_protocol_bridge"]
allowlist = set(bridge["read_only_allowlist"])
blocked = set(bridge["blocked_write_methods"])
forward_tools = bridge["forward_tools"]
manifest = bridge["host_tool_manifest"]

assert bridge["mode"] == "read_only", bridge
assert "akbp.remember" in blocked, bridge
assert "akbp.import_apply" in blocked, bridge
assert "akbp.session.end" in blocked, bridge
assert not allowlist & blocked, bridge
assert "akbp.session.start" in allowlist, bridge
assert "akbp.context" in allowlist, bridge
assert "akbp.search" in allowlist, bridge
assert len(forward_tools) >= 6, bridge
assert manifest["format"] == "akbp-tool-host-manifest-v1", manifest
assert manifest["transport"] == "stdio-jsonl", manifest
assert manifest["server"] == config["server"], manifest
assert manifest["knowledge_base_path"] == config["knowledge_base"]["path"], manifest
assert manifest["default_mode"] == "read_only", manifest
assert "second memory format" in manifest["purpose"], manifest
assert "separate reviewed-write surface" in manifest["approval_boundary"], manifest
assert [tool["forwards_to"] for tool in manifest["tools"]] == [tool["method"] for tool in forward_tools], manifest

for entry, host_tool in zip(forward_tools, manifest["tools"]):
    assert entry["mode"] == "read_only", entry
    assert entry["method"] in allowlist, entry
    assert entry["tool"].startswith("akbp_"), entry
    assert entry["description"], entry
    assert entry["safety"]["writes"] is False, entry
    assert entry["safety"]["requires_review_surface"] is False, entry
    assert entry["params_schema"].startswith("schemas/tool-methods.schema.json#/$defs/"), entry
    assert entry["surface_fields"], entry
    assert host_tool["name"] == entry["tool"], host_tool
    assert host_tool["description"] == entry["description"], host_tool
    assert host_tool["mode"] == "read_only", host_tool
    assert host_tool["safety"] == entry["safety"], host_tool
    assert host_tool["input_schema"] == entry["params_schema"], host_tool
    assert host_tool["preserve_response_fields"] == entry["surface_fields"], host_tool

assert config["safety"]["profile"] == "read_only", config["safety"]
assert config["safety"]["write_policy"] == "no_writes", config["safety"]
assert config["safety"]["host_trust_boundary"]["default_mode"] == "read_only_until_verified", config["safety"]
assert config["quality_gates"]["startup_context"]["require_citations"], config["quality_gates"]
assert config["knowledge_capability"]["type"] == "durable_agent_knowledge", config
assert config["knowledge_capability"]["default_mode"] == "read_only", config
assert "bridge-owned memory format" in config["knowledge_capability"]["not_a"], config
assert "source_backed_claims" in config["knowledge_capability"]["guarantees"], config
print("bridge config contract ok")
PY

python3 "$ROOT/tool-server/akbp_tool_server.py" <<JSONL | python3 -c '
import json
import sys

rows = [json.loads(line) for line in sys.stdin if line.strip()]
by_id = {row["id"]: row for row in rows}

caps = by_id["caps"]
assert caps["ok"], caps
assert caps["result"]["negotiation"]["satisfied"], caps
assert "read_only" in caps["result"]["negotiation"]["supported_profiles"], caps
assert "startup_context" in caps["result"]["negotiation"]["supported_profiles"], caps
print("read-only bridge startup ok")

doctor = by_id["doctor"]
assert doctor["ok"], doctor
assert doctor["result"]["ready_for_adapter"], doctor
assert doctor["result"]["adapter_readiness"]["read_only_ready"], doctor
assert doctor["result"]["adapter_readiness"]["recommended_profile"] in {"read_only", "reviewed_write"}, doctor

start = by_id["session-start"]
assert start["ok"], start
items = start["result"]["context"]["items"]
assert items, start
assert items[0]["citations"], items[0]
assert "read-only wrappers" in items[0]["summary"], items[0]
print("read-only bridge context ok")

blocked = by_id["blocked-write"]
assert not blocked["ok"], blocked
assert blocked["error"]["code"] == "approval_required", blocked
assert blocked["error"]["details"]["method"] == "akbp.remember", blocked
print("direct write blocked ok")
'
{"id":"caps","method":"akbp.capabilities","path":"$KB","params":{"client":"tool-protocol-bridge","requires":["method_param_schemas","capability_negotiation","bounded_context"],"requires_profiles":["read_only","startup_context"]}}
{"id":"doctor","method":"akbp.doctor","path":"$KB","params":{}}
{"id":"session-start","method":"akbp.session.start","path":"$KB","params":{"task":"tool protocol bridge read-only wrappers","limit":5,"max_chars":800}}
{"id":"blocked-write","method":"akbp.remember","path":"$KB","params":{"text":"Direct write tools must stay blocked in read-only bridge mode.","type":"workflow","evidence":["$NOTE"]}}
JSONL

echo "AKBP tool-protocol bridge preflight passed"
