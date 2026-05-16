#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

KB="$TMP/kb"
NOTE="$TMP/freshness-note.md"

echo "AKBP context freshness probe example"

python3 "$ROOT/cli/akbp.py" --path "$KB" init >/dev/null
printf '%s\n' "Decision: startup planning must verify source freshness before using recalled AKBP context." > "$NOTE"
SOURCE_ID="$(python3 "$ROOT/cli/akbp.py" --path "$KB" source add "$NOTE" --type file --title "Fresh startup planning note" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
python3 "$ROOT/cli/akbp.py" --path "$KB" remember "Startup planning must verify source freshness before using recalled AKBP context." --type workflow --confidence 0.93 --evidence "$SOURCE_ID" >/dev/null
python3 "$ROOT/cli/akbp.py" --path "$KB" index --incremental >/dev/null

python3 "$ROOT/cli/akbp.py" --path "$KB" discover | python3 -c '
import json
import sys

discover = json.load(sys.stdin)
probe = discover["context_freshness_probe"]
assert probe["format"] == "akbp-context-freshness-probe-v1", probe
assert probe["safe_default"] == "verify_sources_before_planning_from_recalled_context", probe
assert probe["probe_sequence"][0]["request"]["method"] == "akbp.source.verify", probe
assert probe["probe_sequence"][1]["request"]["method"] == "akbp.session.start", probe
assert "budget_truncated" in probe["fallback_reason_values"], probe
print("discover freshness probe contract ok")
'

python3 "$ROOT/tool-server/akbp_tool_server.py" <<JSONL | python3 -c '
import json
import sys

rows = [json.loads(line) for line in sys.stdin if line.strip()]
by_id = {row["id"]: row for row in rows}

verify = by_id["freshness-source-verify"]
assert verify["ok"], verify
assert verify["result"]["ok"], verify
assert verify["result"]["counts"]["changed"] == 0, verify
assert verify["result"]["counts"]["missing"] == 0, verify

start = by_id["freshness-session-start"]
assert start["ok"], start
context = start["result"]["context"]
assert context["items"], start
assert all(item["citations"] for item in context["items"]), context
assert context["quality"]["ok"], context
assert context["quality"]["require_citations"], context
assert context["quality"]["fail_on_warnings"], context
assert context["quality"]["budget_truncated"] is False, context
assert "source freshness" in json.dumps(context), context
print("fresh startup context trusted ok")
'
{"id":"freshness-source-verify","method":"akbp.source.verify","path":"$KB","params":{"source_id":"$SOURCE_ID","fail_on_issue":true}}
{"id":"freshness-session-start","method":"akbp.session.start","path":"$KB","params":{"task":"startup planning source freshness","limit":5,"max_chars":4000,"min_items":1,"require_citations":true,"fail_on_warnings":true,"fail_on_budget_truncation":true}}
JSONL

printf '%s\n' "Decision: startup planning can skip source freshness checks." > "$NOTE"

python3 "$ROOT/tool-server/akbp_tool_server.py" <<JSONL | python3 -c '
import json
import sys

rows = [json.loads(line) for line in sys.stdin if line.strip()]
by_id = {row["id"]: row for row in rows}

verify = by_id["freshness-source-verify-stale"]
assert verify["ok"], verify
verify_result = verify["result"]
assert not verify_result["ok"], verify_result
assert verify_result["counts"]["changed"] == 1, verify_result
assert verify_result["attention"]["requires_review"], verify_result

start = by_id["freshness-session-start-stale"]
assert not start["ok"], start
assert start["error"]["code"] == "cli_error", start
context = json.loads(start["error"]["details"]["stdout"])
assert context["quality"]["ok"] is False, context
assert context["quality"]["failed"] == ["warnings:1"], context
assert context["warnings"], context
assert "Cited source" in context["warnings"][0], context
print("stale startup context failed closed ok")
'
{"id":"freshness-source-verify-stale","method":"akbp.source.verify","path":"$KB","params":{"source_id":"$SOURCE_ID","fail_on_issue":true}}
{"id":"freshness-session-start-stale","method":"akbp.session.start","path":"$KB","params":{"task":"startup planning source freshness","limit":5,"max_chars":4000,"min_items":1,"require_citations":true,"fail_on_warnings":true,"fail_on_budget_truncation":true}}
JSONL

echo "AKBP context freshness probe example passed"
