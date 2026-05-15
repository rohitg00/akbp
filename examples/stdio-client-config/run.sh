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
assert config["startup"]["method"] == "akbp.capabilities", config
assert config["startup"]["params"]["requires_profiles"] == ["read_only"], config
assert config["health_check"]["method"] == "akbp.doctor", config
assert config["health_check"]["ready_field"] == "ready_for_adapter", config
assert config["safety"]["write_policy"] == "no_writes", config
assert config["safety"]["require_adapter_ready"] is True, config
assert config["session_start"]["method"] == "akbp.session.start", config
print("read-only config ok")
'

python3 "$ROOT/cli/akbp.py" --path "$KB" client-config --name stdio-reviewed-example --profile reviewed-writes --command repo-script |
  python3 -c '
import json, sys

config = json.load(sys.stdin)
assert config["server"]["command"] == "python3", config
assert config["server"]["args"], config
assert config["startup"]["params"]["requires_profiles"] == ["write_review"], config
assert "write_apply_requires_approval" in config["startup"]["params"]["requires"], config
assert config["health_check"]["blocking_field"] == "summary.errors", config
assert config["safety"]["write_policy"] == "dry_run_then_approved", config
assert config["safety"]["require_adapter_ready"] is True, config
assert config["safety"]["require_review_metadata"] is True, config
assert config["safety"]["never_auto_apply_session_end"] is True, config
print("reviewed-write config ok")
'

echo "AKBP stdio client config example passed"
