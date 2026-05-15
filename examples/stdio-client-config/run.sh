#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

KB="$TMP/kb"

echo "AKBP stdio client config example"

python3 "$ROOT/cli/akbp.py" --path "$KB" init >/dev/null

python3 "$ROOT/cli/akbp.py" --path "$KB" client-config --name stdio-readonly-example |
  python3 -c '
import json, sys

config = json.load(sys.stdin)
assert config["transport"] == "stdio-jsonl", config
assert config["startup"]["id"] == "capabilities-1", config
assert config["startup"]["method"] == "akbp.capabilities", config
assert config["startup"]["path"] == config["knowledge_base"]["path"], config
assert config["startup"]["params"]["requires_profiles"] == ["read_only"], config
assert config["health_check"]["id"] == "doctor-1", config
assert config["health_check"]["path"] == config["knowledge_base"]["path"], config
assert config["health_check"]["method"] == "akbp.doctor", config
assert config["health_check"]["ready_field"] == "ready_for_adapter", config
assert [step["run"] for step in config["verification"]] == ["startup", "health_check", "session_start"], config
assert config["verification"][0]["expect"]["result.negotiation.satisfied"] is True, config
assert config["verification"][1]["expect"]["result.summary.errors"] == 0, config
assert config["verification"][2]["expect"]["result.context.items"] == "array", config
assert config["safety"]["write_policy"] == "no_writes", config
assert config["safety"]["host_trust_boundary"]["default_mode"] == "read_only_until_verified", config
assert config["safety"]["require_adapter_ready"] is True, config
assert config["session_start"]["id"] == "session-start-1", config
assert config["session_start"]["method"] == "akbp.session.start", config
assert config["session_start"]["path"] == config["knowledge_base"]["path"], config
print("read-only config ok")
'

python3 "$ROOT/cli/akbp.py" --path "$KB" client-config --name stdio-reviewed-example --profile reviewed-writes --command repo-script |
  python3 -c '
import json, sys

config = json.load(sys.stdin)
assert config["server"]["command"] == "python3", config
assert config["server"]["args"], config
assert config["startup"]["id"] == "capabilities-1", config
assert config["startup"]["path"] == config["knowledge_base"]["path"], config
assert config["startup"]["params"]["requires_profiles"] == ["reviewed_write"], config
assert "write_apply_requires_approval" in config["startup"]["params"]["requires"], config
assert config["health_check"]["id"] == "doctor-1", config
assert config["health_check"]["path"] == config["knowledge_base"]["path"], config
assert config["health_check"]["blocking_field"] == "summary.errors", config
assert config["verification"][0]["run"] == "startup", config
assert config["verification"][1]["run"] == "health_check", config
assert config["verification"][2]["run"] == "session_start", config
assert config["safety"]["write_policy"] == "dry_run_then_approved", config
assert config["safety"]["host_trust_boundary"]["hosted_autonomous_tools"] == "use_read_only_unless_a_separate_human_approval_step_exists", config
assert config["safety"]["require_adapter_ready"] is True, config
assert config["safety"]["require_human_review_surface"] is True, config
assert config["safety"]["require_review_metadata"] is True, config
assert config["safety"]["never_auto_apply_session_end"] is True, config
print("reviewed-write config ok")
'

echo "AKBP stdio client config example passed"
