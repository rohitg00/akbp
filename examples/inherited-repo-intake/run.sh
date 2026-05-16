#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

KB="$TMP/kb"
ISSUE="$TMP/issue-17.md"
PR="$TMP/pr-42.md"
RELEASE="$TMP/release-note.md"
STALE_KB="$TMP/stale-kb"
STALE_NOTE="$TMP/stale-issue.md"

echo "AKBP inherited repo intake example"

python3 "$ROOT/cli/akbp.py" --path "$KB" init >/dev/null

cat > "$ISSUE" <<'NOTE'
# Issue 17

Decision: release fixes must include a rollback checklist before production apply.
NOTE

cat > "$PR" <<'NOTE'
# PR 42

Workflow: payment retry changes need unit coverage and a cited release note before the next agent continues.
NOTE

cat > "$RELEASE" <<'NOTE'
# Release note

Blocker: deployment is paused until source verification and read-only startup context pass.
NOTE

ISSUE_SOURCE="$(python3 "$ROOT/cli/akbp.py" --path "$KB" source add "$ISSUE" --type file --title "Issue 17 release rollback note" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
PR_SOURCE="$(python3 "$ROOT/cli/akbp.py" --path "$KB" source add "$PR" --type file --title "PR 42 payment retry note" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
RELEASE_SOURCE="$(python3 "$ROOT/cli/akbp.py" --path "$KB" source add "$RELEASE" --type file --title "Release pause note" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')"

python3 "$ROOT/cli/akbp.py" --path "$KB" remember "Release fixes must include a rollback checklist before production apply." --type workflow --confidence 0.9 --evidence "$ISSUE_SOURCE" >/dev/null
python3 "$ROOT/cli/akbp.py" --path "$KB" remember "Payment retry changes need unit coverage and a cited release note before another agent continues." --type workflow --confidence 0.9 --evidence "$PR_SOURCE" >/dev/null
python3 "$ROOT/cli/akbp.py" --path "$KB" remember "Deployment is paused until source verification and read-only startup context pass." --type warning --confidence 0.9 --evidence "$RELEASE_SOURCE" >/dev/null
python3 "$ROOT/cli/akbp.py" --path "$KB" index --incremental >/dev/null
python3 "$ROOT/cli/akbp.py" --path "$KB" source verify --fail-on-issue >/dev/null

python3 "$ROOT/cli/akbp.py" --path "$KB" client-config --name inherited-repo-agent --profile read-only | python3 -c '
import json, sys

config = json.load(sys.stdin)
risk_triage = config["inherited_repo_intake"]["takeover_risk_triage"]
assert risk_triage["format"] == "akbp-inherited-repo-risk-triage-v1", config
assert risk_triage["classes"][1]["class"] == "source_verified_read_only", risk_triage
assert "no inherited AKBP memory" in risk_triage["adapter_rule"], risk_triage
assert config["knowledge_capability"]["default_mode"] == "read_only", config
assert config["host_capability_descriptor"]["default_profile"] == "read_only", config
assert config["tool_protocol_bridge_snippets"]["requested_profile"] == "read_only", config
assert config["startup"]["method"] == "akbp.capabilities", config
assert config["session_start"]["method"] == "akbp.session.start", config
assert "akbp.remember" in config["tool_protocol_bridge"]["blocked_write_methods"], config
'

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
assert caps["result"]["profiles"]["read_only"], caps

doctor = by_id["doctor"]
assert doctor["ok"], doctor
assert doctor["result"]["requested_profile"] == "read_only", doctor
assert doctor["result"]["requested_profile_ready"], doctor
assert doctor["result"]["ready_for_adapter"], doctor

start = by_id["start"]
assert start["ok"], start
context = start["result"]["context"]
assert context["items"], context
assert all(item["citations"] for item in context["items"]), context
assert context["quality"]["ok"], context
assert context["quality"]["require_citations"], context
assert context["quality"]["fail_on_warnings"], context
assert "rollback checklist" in json.dumps(context), context

blocked = by_id["write-blocked"]
assert not blocked["ok"], blocked
assert blocked["error"]["code"] == "approval_required", blocked

print("read-only inherited repo startup ok")
print("unapproved inherited repo write blocked ok")
'
{"id":"caps","method":"akbp.capabilities","path":"$KB","params":{"client":"inherited-repo-agent","requires":["method_param_schemas","capability_negotiation","bounded_context"],"requires_profiles":["read_only","startup_context"]}}
{"id":"doctor","method":"akbp.doctor","path":"$KB","params":{"profile":"read_only"}}
{"id":"start","method":"akbp.session.start","path":"$KB","params":{"task":"take over inherited repo release work safely","limit":5,"max_chars":4000,"min_items":1,"require_citations":true,"fail_on_warnings":true}}
{"id":"write-blocked","method":"akbp.remember","path":"$KB","params":{"text":"Takeover agent can directly rewrite durable repo memory.","type":"workflow","evidence":["$ISSUE_SOURCE"]}}
JSONL

python3 "$ROOT/cli/akbp.py" --path "$KB" context "take over inherited repo release work safely" --limit 5 --fail-on-warnings | python3 -c '
import json, sys

data = json.load(sys.stdin)
assert data["items"], data
assert all(item["citations"] for item in data["items"]), data
assert "rollback checklist" in json.dumps(data), data
print("cited inherited repo context ok")
'

python3 "$ROOT/cli/akbp.py" --path "$STALE_KB" init >/dev/null
printf '%s\n' "Decision: inherited repo fixes require a rollback checklist." > "$STALE_NOTE"
STALE_SOURCE="$(python3 "$ROOT/cli/akbp.py" --path "$STALE_KB" source add "$STALE_NOTE" --type file --title "Stale inherited repo note" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
python3 "$ROOT/cli/akbp.py" --path "$STALE_KB" remember "Inherited repo fixes require a rollback checklist." --type workflow --confidence 0.9 --evidence "$STALE_SOURCE" >/dev/null
python3 "$ROOT/cli/akbp.py" --path "$STALE_KB" index --incremental >/dev/null
printf '%s\n' "Decision: inherited repo fixes can skip rollback checklists." > "$STALE_NOTE"

python3 "$ROOT/cli/akbp.py" --path "$STALE_KB" source verify --fail-on-issue > "$TMP/stale-source-verify.json" || true
python3 - "$TMP/stale-source-verify.json" <<'PY'
import json
import sys

data = json.loads(open(sys.argv[1], encoding="utf-8").read())
assert not data["ok"], data
assert data["counts"]["changed"] == 1, data
assert data["attention"]["requires_review"], data
assert data["attention"]["recommended_action"] == "review_affected_claims", data
assert data["attention"]["affected_claims"], data
print("stale inherited repo evidence requires review ok")
PY

STALE_CONTEXT_JSON="$TMP/stale-context.json"
if python3 "$ROOT/cli/akbp.py" --path "$STALE_KB" context "inherited repo rollback checklist" --limit 5 --min-items 1 --require-citations --fail-on-warnings > "$STALE_CONTEXT_JSON"; then
  echo "expected stale inherited repo context to fail on source drift" >&2
  exit 1
fi
python3 - "$STALE_CONTEXT_JSON" <<'PY'
import json
import sys

data = json.loads(open(sys.argv[1], encoding="utf-8").read())
assert data["warnings"], data
assert data["quality"]["failed"] == ["warnings:1"], data
assert "Cited source" in data["warnings"][0], data
print("stale inherited repo context blocked ok")
PY

echo "AKBP inherited repo intake example passed"
