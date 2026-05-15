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

unsupported = envelope("caps-unsupported")
assert unsupported["ok"], unsupported
unsupported_negotiation = unsupported["result"]["negotiation"]
assert unsupported_negotiation["satisfied"] is False, unsupported
assert unsupported_negotiation["supported_features"] == ["method_param_schemas"], unsupported
assert unsupported_negotiation["unsupported_features"] == ["hosted_dashboard"], unsupported
assert unsupported_negotiation["supported_profiles"] == ["startup_context"], unsupported
assert unsupported_negotiation["unsupported_profiles"] == ["autonomous_write"], unsupported
print("unsupported capability gate ok")

invalid_params = envelope("session-start-invalid-params")
assert not invalid_params["ok"], invalid_params
assert invalid_params["error"]["code"] == "invalid_params", invalid_params
invalid_details = invalid_params["error"]["details"]
assert invalid_details["params_schema"].endswith("#/$defs/akbp.session.start.params"), invalid_params
assert "limit must be between 1 and 100" in invalid_details["type_errors"], invalid_params
print("invalid params repair contract ok")

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

truncated = envelope("session-start-truncated")
assert truncated["ok"], truncated
truncated_context = truncated["result"]["context"]
budget = truncated_context["budget"]
assert budget["max_chars"] == 24, truncated
assert budget["truncated"] is True, truncated
assert budget["truncated_items"] >= 1, truncated
assert budget["items_before_budget"] >= budget["items_after_budget"], truncated
assert any("Context budget truncated" in warning for warning in truncated_context["warnings"]), truncated
assert truncated_context["quality"]["ok"] is True, truncated
print("budget truncation contract ok")

preview = envelope("remember-preview")
assert preview["ok"], preview
review = preview["result"]
for field in ("dry_run", "review_required", "apply_instruction", "method", "path", "argv", "redacted", "would_write"):
    assert field in review, review
assert review["dry_run"] is True, review
assert review["review_required"] is True, review
assert review["would_write"] is True, review
assert review["method"] == "akbp.remember", review
assert review["preview_fingerprint"].startswith("sha256:"), review
print("dry-run review contract ok")

blocked = envelope("remember-blocked")
assert not blocked["ok"], blocked
assert blocked["error"]["code"] == "approval_required", blocked
details = blocked["error"]["details"]
assert details["method"] == "akbp.remember", blocked
assert details["dry_run"] is False, blocked
assert details["review_required"] is True, blocked
assert details["apply_instruction"], blocked
assert details["preview_fingerprint"] == review["preview_fingerprint"], blocked
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
{"id":"caps-unsupported","method":"akbp.capabilities","path":"$KB","params":{"client":"structured-output-harness-example","requires":["method_param_schemas","hosted_dashboard"],"requires_profiles":["startup_context","autonomous_write"]}}
{"id":"session-start-invalid-params","method":"akbp.session.start","path":"$KB","params":{"task":"adapter structured output harness","limit":0}}
{"id":"doctor","method":"akbp.doctor","path":"$KB"}
{"id":"session-start","method":"akbp.session.start","path":"$KB","params":{"task":"adapter structured output harness","limit":5,"max_chars":500}}
{"id":"session-start-truncated","method":"akbp.session.start","path":"$KB","params":{"task":"adapter structured output harness","limit":5,"max_chars":24,"min_items":1,"require_citations":true}}
{"id":"remember-preview","method":"akbp.remember","path":"$KB","dry_run":true,"params":{"text":"Adapter harnesses should fail closed when AKBP response shape validation fails.","type":"workflow","evidence":["$NOTE"]}}
{"id":"remember-blocked","method":"akbp.remember","path":"$KB","params":{"text":"Adapter harnesses should fail closed when AKBP response shape validation fails.","type":"workflow","evidence":["$NOTE"]}}
{"id":"remember-approved","method":"akbp.remember","path":"$KB","approved":true,"params":{"text":"Adapter harnesses should fail closed when AKBP response shape validation fails.","type":"workflow","evidence":["$NOTE"]}}
{"id":"index-approved","method":"akbp.index","path":"$KB","approved":true,"params":{"incremental":true}}
{"id":"recall-approved","method":"akbp.context","path":"$KB","params":{"task":"response shape validation fails","limit":5,"max_chars":500}}
JSONL

python3 "$ROOT/cli/akbp.py" --path "$KB" client-config --name structured-output-harness --profile reviewed-writes | python3 -c '
import json
import sys

config = json.load(sys.stdin)

prompt_contract = config["adapter_prompt_contract"]
assert prompt_contract["format"] == "akbp-adapter-prompt-contract-v1", prompt_contract
assert prompt_contract["profile"] == "reviewed_write", prompt_contract
assert prompt_contract["startup_request"]["method"] == "akbp.session.start", prompt_contract
assert prompt_contract["startup_request"]["params"]["max_chars"] == 4000, prompt_contract
assert prompt_contract["startup_request"]["params"]["min_items"] == 1, prompt_contract
assert prompt_contract["startup_request"]["params"]["require_citations"] is True, prompt_contract
assert prompt_contract["planning_gate"]["required_before_planning"], prompt_contract
trust_gate = prompt_contract["startup_trust_gate"]
assert trust_gate["format"] == "akbp-startup-trust-gate-v1", trust_gate
assert trust_gate["required_before_planning"], trust_gate
assert trust_gate["trust_conditions"]["minimum_items"] == 1, trust_gate
assert trust_gate["trust_conditions"]["require_citations"], trust_gate
assert "result.context.items is empty" in trust_gate["fail_closed_on"], trust_gate
assert "Continue without recalled AKBP memory" in trust_gate["fallback_action"], trust_gate
assert "ok" in prompt_contract["validation"]["branch_on"], prompt_contract
assert "error.code" in prompt_contract["validation"]["branch_on"], prompt_contract
assert "result.context.budget" in prompt_contract["validation"]["preserve_fields"], prompt_contract

rules = " ".join(prompt_contract["system_rules"])
assert "Before planning" in rules, prompt_contract
assert "Use only cited context" in rules, prompt_contract
assert "approved:true" in rules, prompt_contract
assert "error.code" in rules, prompt_contract

first_run = config["first_run_sequence"]
assert "keep the integration read-only" in first_run["stop_policy"], first_run
steps = {step["step"]: step for step in first_run["steps"]}
assert steps["negotiate_capabilities"]["expect"]["result.negotiation.satisfied"], first_run
assert steps["check_adapter_readiness"]["expect"]["result.adapter_readiness.reviewed_write_ready"], first_run
assert steps["retrieve_cited_startup_context"]["expect"]["result.context.budget.max_chars"] == 4000, first_run
assert steps["enable_writes_only_after_review_surface"]["expect"]["approval_outside_model_tool_call"], first_run

print("prompt contract harness ok")
'

echo "AKBP structured output harness example passed"
