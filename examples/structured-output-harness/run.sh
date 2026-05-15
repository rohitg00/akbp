#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

KB="$TMP/kb"
NOTE="$TMP/harness-note.md"

echo "AKBP structured output harness example"

python3 "$ROOT/cli/akbp.py" --path "$KB" init >/dev/null
printf '%s\n' "Adapter harnesses should validate response envelopes, schema-backed fields, citations, and approval stop signals before trusting memory." > "$NOTE"
python3 "$ROOT/cli/akbp.py" --path "$KB" source add "$NOTE" --type file --title "Adapter harness note" >/dev/null
python3 "$ROOT/cli/akbp.py" --path "$KB" remember "Adapter harnesses should validate structured AKBP responses before trusting recalled context or applying writes." --type workflow --confidence 0.92 --evidence "$NOTE" >/dev/null
python3 "$ROOT/cli/akbp.py" --path "$KB" index --incremental >/dev/null

python3 "$ROOT/tool-server/akbp_tool_server.py" <<JSONL | python3 -c '
import json
import sys

rows = [json.loads(line) for line in sys.stdin if line.strip()]
by_id = {row["id"]: row for row in rows}

def envelope(row_id):
    row = by_id[row_id]
    assert set(row) == {"id", "ok", "result", "error"}, row
    assert row["id"] == row_id, row
    if row["ok"]:
        assert row["result"] is not None, row
        assert row["error"] is None, row
    else:
        assert row["result"] is None, row
        assert isinstance(row["error"], dict), row
        assert "code" in row["error"], row
    return row

caps = envelope("caps")
assert caps["ok"], caps
features = caps["result"]["features"]
negotiation = caps["result"]["negotiation"]
assert features["method_param_schemas"], caps
assert features["structured_errors"], caps
assert features["write_apply_requires_approval"], caps
assert negotiation["satisfied"], caps
assert "startup_context" in negotiation["supported_profiles"], caps
assert "reviewed_write" in negotiation["supported_profiles"], caps
assert caps["result"]["profile_contracts"]["reviewed_write"]["write_policy"] == "dry_run_preview_then_approved_apply", caps
assert caps["result"]["methods"]["akbp.remember"]["write"], caps
assert caps["result"]["methods"]["akbp.remember"]["review_required"], caps
print("capability contract ok")

doctor = envelope("doctor")
assert doctor["ok"], doctor
assert doctor["result"]["ready_for_adapter"], doctor
assert doctor["result"]["adapter_readiness"]["reviewed_write_ready"], doctor
posture = doctor["result"]["security_posture"]
assert posture["write_boundary"] == "dry_run_preview_then_approved_apply", doctor
assert posture["approval_field"] == "approved", doctor
assert "akbp.import_check" in posture["safe_review_methods"], doctor
print("doctor contract ok")

start = envelope("session-start")
assert start["ok"], start
result = start["result"]
assert result["task"] == "adapter structured output harness", start
assert result["context"]["items"], start
first = result["context"]["items"][0]
assert first["type"] == "claim", first
assert first["citations"], first
assert "structured AKBP responses" in first["summary"], first
print("startup context contract ok")

preview = envelope("remember-preview")
assert preview["ok"], preview
review = preview["result"]
for field in ("dry_run", "review_required", "apply_instruction", "method", "path", "argv", "redacted", "would_write"):
    assert field in review, review
assert review["dry_run"] is True, review
assert review["review_required"] is True, review
assert review["would_write"] is True, review
assert review["method"] == "akbp.remember", review
print("dry-run review contract ok")

blocked = envelope("remember-blocked")
assert not blocked["ok"], blocked
assert blocked["error"]["code"] == "approval_required", blocked
details = blocked["error"]["details"]
assert details["method"] == "akbp.remember", blocked
assert details["dry_run"] is False, blocked
assert details["review_required"] is True, blocked
assert details["apply_instruction"], blocked
print("approval-required contract ok")

approved = envelope("remember-approved")
assert approved["ok"], approved
claim = approved["result"]
assert claim["type"] == "workflow", approved
assert claim["text"] == "Adapter harnesses should fail closed when AKBP response shape validation fails.", approved
assert len(claim["evidence"]) == 1 and claim["evidence"][0].endswith("harness-note.md"), approved
print("approved apply contract ok")

index = envelope("index-approved")
assert index["ok"], index
assert index["result"]["ok"], index

recall = envelope("recall-approved")
assert recall["ok"], recall
recall_items = recall["result"]["items"]
assert recall_items, recall
assert any("response shape validation fails" in item["summary"] for item in recall_items), recall
assert any(item["citations"] for item in recall_items), recall
print("approved recall contract ok")
'
{"id":"caps","method":"akbp.capabilities","path":"$KB","params":{"client":"structured-output-harness-example","requires":["method_param_schemas","structured_errors","write_apply_requires_approval"],"requires_profiles":["startup_context","reviewed_write"]}}
{"id":"doctor","method":"akbp.doctor","path":"$KB"}
{"id":"session-start","method":"akbp.session.start","path":"$KB","params":{"task":"adapter structured output harness","limit":5,"max_chars":500}}
{"id":"remember-preview","method":"akbp.remember","path":"$KB","dry_run":true,"params":{"text":"Adapter harnesses should fail closed when AKBP response shape validation fails.","type":"workflow","evidence":["$NOTE"]}}
{"id":"remember-blocked","method":"akbp.remember","path":"$KB","params":{"text":"Unapproved adapter harness writes must fail closed.","type":"workflow","evidence":["$NOTE"]}}
{"id":"remember-approved","method":"akbp.remember","path":"$KB","approved":true,"params":{"text":"Adapter harnesses should fail closed when AKBP response shape validation fails.","type":"workflow","evidence":["$NOTE"]}}
{"id":"index-approved","method":"akbp.index","path":"$KB","approved":true,"params":{"incremental":true}}
{"id":"recall-approved","method":"akbp.context","path":"$KB","params":{"task":"response shape validation fails","limit":5,"max_chars":500}}
JSONL

echo "AKBP structured output harness example passed"
