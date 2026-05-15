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
assert config["runtime_requirements"]["local_first"] is True, config
assert config["runtime_requirements"]["network_required"] is False, config
assert config["runtime_requirements"]["cloud_account_required"] is False, config
assert config["runtime_requirements"]["secrets_required"] == [], config
assert "AKBP artifacts" in config["runtime_requirements"]["durable_state_owner"], config
first_run = config["first_run_sequence"]
assert "ordered setup path" in first_run["purpose"], config
assert "keep the integration read-only" in first_run["stop_policy"], config
assert [step["step"] for step in first_run["steps"]] == [
    "resolve_knowledge_base",
    "negotiate_capabilities",
    "check_adapter_readiness",
    "retrieve_cited_startup_context",
    "enable_writes_only_after_review_surface",
], config
assert first_run["steps"][0]["expect"]["knowledge_base.path"] == config["knowledge_base"]["path"], config
assert first_run["steps"][1]["request_id"] == "capabilities-1", config
assert first_run["steps"][2]["request_id"] == "doctor-1", config
assert first_run["steps"][3]["request_id"] == "session-start-1", config
assert first_run["steps"][4]["required"] is False, config
assert config["knowledge_capability"]["type"] == "durable_agent_knowledge", config
assert config["knowledge_capability"]["default_mode"] == "read_only", config
assert config["knowledge_capability"]["write_mode"] == "reviewed_write_only", config
assert "source_backed_claims" in config["knowledge_capability"]["guarantees"], config
assert "automatic background write sink" in config["knowledge_capability"]["not_a"], config
assert "approved:true" in config["knowledge_capability"]["host_mapping"]["apply"], config
multi_client = config["multi_client_scope"]
assert multi_client["shared_kb_path"] == config["knowledge_base"]["path"], config
assert multi_client["client_identity_field"] == "startup.params.client", config
assert multi_client["default_mode"] == "read_only", config
assert "same selected knowledge_base.path" in multi_client["scope_rule"], config
assert "Runtime scratchpads" in multi_client["isolation_rule"], config
assert "supersede or contradict" in multi_client["conflict_policy"], config
assert multi_client["safe_for_public_templates"] is False, config
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
assert config["tool_protocol_bridge"]["mode"] == "read_only", config
assert "akbp.session.start" in config["tool_protocol_bridge"]["read_only_allowlist"], config
assert "akbp.remember" in config["tool_protocol_bridge"]["blocked_write_methods"], config
first_tool = config["tool_protocol_bridge"]["forward_tools"][0]
assert "Discover supported AKBP methods" in first_tool["description"], config
assert first_tool["safety"]["writes"] is False, config
assert first_tool["safety"]["requires_review_surface"] is False, config
assert first_tool["safety"]["approval"] == "not_applicable", config
client_manifest = config["tool_protocol_bridge"]["client_tool_manifest"]
assert client_manifest["format"] == "akbp-client-tool-manifest-v1", config
assert client_manifest["transport_adapter"] == "stdio-jsonl-to-host-tools", config
assert client_manifest["response_contract"]["branch_on"] == "error.code", config
assert client_manifest["response_contract"]["surface_citations"] is True, config
assert [tool["akbp_method"] for tool in client_manifest["tools"]] == config["tool_protocol_bridge"]["read_only_allowlist"], config
assert client_manifest["tools"][0]["description"] == first_tool["description"], config
assert client_manifest["tools"][0]["safety"] == first_tool["safety"], config
assert "akbp.remember" in client_manifest["blocked_write_methods"], config
assert "dry-run previews" in client_manifest["approval_boundary"], config
manifest = config["tool_protocol_bridge"]["host_tool_manifest"]
assert [request["id"] for request in manifest["preflight_requests"]] == ["capabilities-1", "doctor-1", "session-start-1"], config
assert manifest["preflight_requests"][0]["params"]["requires_profiles"] == ["read_only"], config
assert manifest["preflight_requests"][0]["expect"]["result.negotiation.satisfied"] is True, config
assert manifest["preflight_requests"][1]["method"] == "akbp.doctor", config
assert manifest["preflight_requests"][2]["params"]["max_chars"] == 4000, config
assert client_manifest["preflight_requests"] == manifest["preflight_requests"], config
assert config["session_start"]["id"] == "session-start-1", config
assert config["session_start"]["method"] == "akbp.session.start", config
assert config["session_start"]["path"] == config["knowledge_base"]["path"], config
assert config["response_contract"]["envelope"]["required"] == ["id", "ok", "result", "error"], config
assert config["response_contract"]["envelope"]["ok"] == "boolean", config
assert config["response_contract"]["schemas"]["response"] == "schemas/tool-response.schema.json", config
actions = config["response_contract"]["error_actions"]
assert actions["invalid_json"]["adapter_action"].startswith("repair JSON serialization"), config
assert actions["unknown_method"]["retry"] == "only after capability refresh", config
assert "params_schema" in actions["invalid_params"]["adapter_action"], config
assert "approved:true" in actions["approval_required"]["retry"], config
assert actions["cli_error"]["write_policy"] == "do not assume a durable write happened", config
assert actions["internal_error"]["retry"] == "do not auto-retry writes", config
print("read-only config ok")
'

python3 "$ROOT/cli/akbp.py" --path "$KB" client-config --name stdio-portable-example --portable |
  python3 -c '
import json, sys

config = json.load(sys.stdin)
assert config["knowledge_base"]["path"] == "<AKBP_KB_PATH>", config
assert config["knowledge_base"]["card"] == "<AKBP_KB_PATH>/akbp.json", config
assert config["knowledge_base"]["portable_template"] is True, config
assert config["first_run_sequence"]["steps"][0]["expect"]["knowledge_base.path"] == "<AKBP_KB_PATH>", config
assert "<AKBP_KB_PATH>" in config["runtime_requirements"]["path_resolution"], config
assert config["startup"]["path"] == "<AKBP_KB_PATH>", config
assert config["health_check"]["path"] == "<AKBP_KB_PATH>", config
assert config["session_start"]["path"] == "<AKBP_KB_PATH>", config
assert config["multi_client_scope"]["shared_kb_path"] == "<AKBP_KB_PATH>", config
assert config["multi_client_scope"]["safe_for_public_templates"] is True, config
assert config["distribution"]["safe_to_commit"] is True, config
assert config["distribution"]["replace_before_run"] == ["<AKBP_KB_PATH>"], config
print("portable config ok")
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
assert config["first_run_sequence"]["steps"][4]["required"] is True, config
assert config["first_run_sequence"]["steps"][4]["expect"]["approval_outside_model_tool_call"] is True, config
assert config["health_check"]["id"] == "doctor-1", config
assert config["health_check"]["path"] == config["knowledge_base"]["path"], config
assert config["health_check"]["blocking_field"] == "summary.errors", config
assert config["verification"][0]["run"] == "startup", config
assert config["verification"][1]["run"] == "health_check", config
assert config["verification"][2]["run"] == "session_start", config
assert "Branch on error.code" in config["response_contract"]["error_rules"][0], config
assert config["response_contract"]["schemas"]["methods"] == "schemas/tool-methods.schema.json", config
assert config["safety"]["write_policy"] == "dry_run_then_approved", config
assert config["safety"]["host_trust_boundary"]["hosted_autonomous_tools"] == "use_read_only_unless_a_separate_human_approval_step_exists", config
assert config["safety"]["require_adapter_ready"] is True, config
assert config["safety"]["require_human_review_surface"] is True, config
assert config["safety"]["require_review_metadata"] is True, config
assert config["safety"]["never_auto_apply_session_end"] is True, config
assert config["tool_protocol_bridge"]["mode"] == "reviewed_write", config
assert config["tool_protocol_bridge"]["client_tool_manifest"]["default_mode"] == "read_only", config
assert "akbp.ingest" in config["tool_protocol_bridge"]["client_tool_manifest"]["blocked_write_methods"], config
assert config["tool_protocol_bridge"]["reviewed_write_tools"][0]["required_flags"] == {"dry_run": True}, config
reviewed_tools = {tool["tool"]: tool for tool in config["tool_protocol_bridge"]["reviewed_write_tools"]}
assert reviewed_tools["akbp_ingest_preview"]["method"] == "akbp.ingest", config
assert reviewed_tools["akbp_ingest_preview"]["required_flags"] == {"dry_run": True}, config
assert reviewed_tools["akbp_apply_reviewed"]["required_flags"] == {"approved": True}, config
assert reviewed_tools["akbp_index_apply"]["method"] == "akbp.index", config
assert reviewed_tools["akbp_index_apply"]["required_flags"] == {"approved": True}, config
assert "exact reviewed method" in config["tool_protocol_bridge"]["apply_rule"], config
print("reviewed-write config ok")
'

echo "AKBP stdio client config example passed"
