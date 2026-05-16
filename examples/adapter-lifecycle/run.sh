#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

KB="$TMP/kb"
TRANSCRIPT="$ROOT/examples/adapter-lifecycle/session-summary.md"

echo "AKBP adapter lifecycle example"

python3 "$ROOT/cli/akbp.py" --path "$KB" init >/dev/null
python3 "$ROOT/cli/akbp.py" --path "$KB" source add "$ROOT/docs/TOOL_CONTRACT.md" --type file --title "Tool contract" >/dev/null
python3 "$ROOT/cli/akbp.py" --path "$KB" remember "Adapters should call akbp.session.start before planning so retrieved AKBP context can be cited." --type workflow --confidence 0.9 --evidence "$ROOT/docs/TOOL_CONTRACT.md" >/dev/null
python3 "$ROOT/cli/akbp.py" --path "$KB" index --incremental >/dev/null

python3 "$ROOT/tool-server/akbp_tool_server.py" <<JSONL | python3 -c '
import json, pathlib, sys

rows = [json.loads(line) for line in sys.stdin if line.strip()]
by_id = {row["id"]: row for row in rows}

caps = by_id["caps"]
assert caps["ok"], caps
negotiation = caps["result"]["negotiation"]
assert negotiation["satisfied"], negotiation
assert negotiation["unsupported_features"] == [], negotiation
assert negotiation["unsupported_profiles"] == [], negotiation
assert "startup_context" in negotiation["supported_profiles"], negotiation
assert "reviewed_write" in negotiation["supported_profiles"], negotiation
assert "akbp.session.start" in caps["result"]["methods"], caps
assert "akbp.session.end" in caps["result"]["methods"], caps
assert caps["result"]["features"]["method_param_schemas"], caps
print("capabilities ok")

start = by_id["lifecycle-start"]
assert start["ok"], start
start_result = start["result"]
assert start_result["session_id"].startswith("adapter_session_"), start_result
assert start_result["task"] == "plan adapter session start wiring", start_result
context = start_result["context"]
assert context["items"], context
first = context["items"][0]
assert first["citations"], first
assert "akbp.session.start before planning" in first["summary"], first
print("session start ok")

gated = by_id["lifecycle-start-gated"]
assert gated["ok"], gated
gated_context = gated["result"]["context"]
assert gated_context["quality"]["trusted_for_planning"], gated_context
assert gated_context["quality"]["fallback_reason"] is None, gated_context
assert gated_context["items"], gated_context
assert gated_context["items"][0]["citations"], gated_context
print("cited startup gate ok")

preview = by_id["lifecycle-end-preview"]
assert preview["ok"], preview
preview_result = preview["result"]
assert preview_result["dry_run"], preview_result
assert preview_result["review_required"], preview_result
assert preview_result["apply_instruction"], preview_result
assert preview_result["created_claims"] == [], preview_result
assert "Use `akbp.session.start` at startup" in " ".join(preview_result["summary"]["decisions"]), preview_result
assert pathlib.Path(preview_result["page"]).name.startswith("session_"), preview_result
print("session end preview ok")

blocked = by_id["lifecycle-end-blocked"]
assert not blocked["ok"], blocked
assert blocked["error"]["code"] == "approval_required", blocked
assert blocked["error"]["details"]["review_required"], blocked
print("unapproved session end blocked")

applied = by_id["lifecycle-end-apply"]
assert applied["ok"], applied
apply_result = applied["result"]
assert apply_result["apply"], apply_result
assert not apply_result["dry_run"], apply_result
assert apply_result["source_id"], apply_result
assert apply_result["created_claims"], apply_result
print("session end apply ok")

indexed = by_id["lifecycle-index"]
assert indexed["ok"], indexed

recall = by_id["lifecycle-recall"]
assert recall["ok"], recall
items = recall["result"]["items"]
assert items, recall
summaries = " ".join(item.get("summary", "") for item in items)
assert "approved lifecycle writes" in summaries or "adapter-lifecycle/session-summary.md" in summaries, recall
print("lifecycle recall ok")
'
{"id":"caps","method":"akbp.capabilities","path":"$KB","params":{"client":"adapter-lifecycle-example","requires":["method_param_schemas","capability_negotiation","write_apply_requires_approval"],"requires_profiles":["startup_context","reviewed_write"]}}
{"id":"lifecycle-start","method":"akbp.session.start","path":"$KB","params":{"task":"plan adapter session start wiring","limit":5}}
{"id":"lifecycle-start-gated","method":"akbp.session.start","path":"$KB","params":{"task":"plan adapter session start wiring","limit":5,"min_items":1,"require_citations":true,"fail_on_warnings":true}}
{"id":"lifecycle-end-preview","method":"akbp.session.end","path":"$KB","dry_run":true,"params":{"transcript":"$TRANSCRIPT","apply":true}}
{"id":"lifecycle-end-blocked","method":"akbp.session.end","path":"$KB","params":{"transcript":"$TRANSCRIPT","apply":true}}
{"id":"lifecycle-end-apply","method":"akbp.session.end","path":"$KB","approved":true,"params":{"transcript":"$TRANSCRIPT","apply":true}}
{"id":"lifecycle-index","method":"akbp.index","path":"$KB","approved":true,"params":{"incremental":true}}
{"id":"lifecycle-recall","method":"akbp.context","path":"$KB","params":{"task":"continue adapter lifecycle integration","limit":5}}
JSONL

python3 "$ROOT/cli/akbp.py" --path "$KB" conformance --level 2 >/dev/null

echo "AKBP adapter lifecycle example passed"
