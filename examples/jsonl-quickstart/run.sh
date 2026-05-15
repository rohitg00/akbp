#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

KB="$TMP/kb"
NOTE="$TMP/adapter-note.md"

echo "AKBP JSONL quickstart example"

python3 "$ROOT/cli/akbp.py" --path "$KB" init >/dev/null
printf '%s\n' "Adapter quickstarts should prove cited startup context before enabling writes." > "$NOTE"
python3 "$ROOT/cli/akbp.py" --path "$KB" source add "$NOTE" --type file --title "Adapter note" >/dev/null
python3 "$ROOT/cli/akbp.py" --path "$KB" remember "Adapters should retrieve cited startup context before enabling write-capable memory." --type workflow --confidence 0.91 --evidence "$NOTE" >/dev/null
python3 "$ROOT/cli/akbp.py" --path "$KB" index --incremental >/dev/null

python3 "$ROOT/tool-server/akbp_tool_server.py" <<JSONL | python3 -c '
import json
import sys

rows = [json.loads(line) for line in sys.stdin if line.strip()]
by_id = {row["id"]: row for row in rows}

caps = by_id["caps"]
assert caps["ok"], caps
assert caps["result"]["features"]["method_param_schemas"], caps
assert caps["result"]["features"]["approval_required_errors"], caps
assert caps["result"]["features"]["write_apply_requires_approval"], caps
assert "akbp.session.start" in caps["result"]["methods"], caps
assert "akbp.remember" in caps["result"]["methods"], caps
assert "akbp.export" in caps["result"]["methods"], caps
assert caps["result"]["negotiation"]["satisfied"], caps
print("capability discovery ok")

start = by_id["session-start"]
assert start["ok"], start
context = start["result"]["context"]
assert context["items"], context
assert context["items"][0]["citations"], context
assert "startup context" in context["items"][0]["summary"], context
print("session start cited context ok")

preview = by_id["remember-preview"]
assert preview["ok"], preview
assert preview["result"]["dry_run"], preview
assert preview["result"]["review_required"], preview
assert preview["result"]["apply_instruction"], preview
assert preview["result"]["would_write"], preview
print("dry-run write preview ok")

blocked = by_id["remember-blocked"]
assert not blocked["ok"], blocked
assert blocked["error"]["code"] == "approval_required", blocked
assert blocked["error"]["details"]["review_required"], blocked
print("unapproved write blocked ok")

approved = by_id["remember-approved"]
assert approved["ok"], approved
assert approved["result"]["id"].startswith("claim_"), approved
assert approved["result"]["text"] == "Adapters must show a dry-run memory preview before approved durable writes.", approved
print("approved write apply ok")

indexed = by_id["index-approved"]
assert indexed["ok"], indexed
assert indexed["result"]["rows"] >= 1, indexed
print("index refresh ok")

recall = by_id["context-after-apply"]
assert recall["ok"], recall
items = recall["result"]["items"]
assert items, recall
joined = " ".join(item.get("summary", "") for item in items)
assert "dry-run memory preview" in joined, recall
assert any(item.get("citations") for item in items), recall
print("cited recall ok")

exported = by_id["export"]
assert exported["ok"], exported
bundle = exported["result"]
assert bundle["manifest"]["format"] == "akbp-portable-bundle", bundle
assert bundle["manifest"]["safety"]["excludes_local_state"], bundle
assert bundle["manifest"]["safety"]["excludes_indexes"], bundle
assert bundle["manifest"]["counts"]["claims"] >= 2, bundle
print("portable export ok")
'
{"id":"caps","method":"akbp.capabilities","path":"$KB","params":{"client":"jsonl-quickstart-example","requires":["method_param_schemas","approval_required_errors","write_apply_requires_approval"],"requires_profiles":["startup_context","reviewed_write","portability"]}}
{"id":"session-start","method":"akbp.session.start","path":"$KB","params":{"task":"plan adapter write safety","limit":5}}
{"id":"remember-preview","method":"akbp.remember","path":"$KB","dry_run":true,"params":{"text":"Adapters must show a dry-run memory preview before approved durable writes.","type":"workflow"}}
{"id":"remember-blocked","method":"akbp.remember","path":"$KB","params":{"text":"Adapters must show a dry-run memory preview before approved durable writes.","type":"workflow"}}
{"id":"remember-approved","method":"akbp.remember","path":"$KB","approved":true,"params":{"text":"Adapters must show a dry-run memory preview before approved durable writes.","type":"workflow"}}
{"id":"index-approved","method":"akbp.index","path":"$KB","approved":true,"params":{"incremental":true}}
{"id":"context-after-apply","method":"akbp.context","path":"$KB","params":{"task":"continue dry-run memory preview adapter workflow","limit":5}}
{"id":"export","method":"akbp.export","path":"$KB"}
JSONL

echo "AKBP JSONL quickstart example passed"
