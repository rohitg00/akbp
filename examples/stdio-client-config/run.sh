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
scope = config["scope_selection"]
assert scope["selected_scope"] == "repo_local", config
assert scope["selected_kb_path"] == config["knowledge_base"]["path"], config
assert scope["safe_default"] == "repo_local_read_only", config
assert "Which reviewed AKBP knowledge base" in scope["installer_prompt"], config
assert [option["scope"] for option in scope["scope_options"]] == [
    "repo_local",
    "team_shared",
    "personal_assistant",
    "migration",
], config
assert scope["scope_options"][0]["recommended"] is True, config
assert scope["scope_options"][0]["default_profile"] == "read_only", config
assert "private chat exports" in scope["scope_options"][0]["avoid"], config
assert "outside public repos" in scope["scope_options"][2]["trust_boundary"], config
assert "import-check" in scope["scope_options"][3]["trust_boundary"], config
assert "selected_kb_path" in scope["adapter_rules"][0], config
assert "setup UI" in scope["adapter_rules"][3], config
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
bridge_snippets = config["tool_protocol_bridge_snippets"]
assert bridge_snippets["format"] == "akbp-tool-protocol-bridge-snippets-v1", config
assert bridge_snippets["direct_host_native_server"] is False, config
assert bridge_snippets["bridge_required"] is True, config
assert "without claiming" in bridge_snippets["purpose"], config
assert bridge_snippets["safe_default_profile"] == "read_only", config
assert bridge_snippets["requested_profile"] == "read_only", config
assert bridge_snippets["server_process"]["transport"] == "stdio-jsonl", config
assert bridge_snippets["server_process"]["env"]["AKBP_KB_PATH"] == config["knowledge_base"]["path"], config
assert bridge_snippets["host_server_template"]["toolServers"]["akbp"]["command"] == "<AKBP_TOOL_BRIDGE_COMMAND>", config
assert bridge_snippets["preflight_requests"] == config["tool_protocol_bridge"]["host_tool_manifest"]["preflight_requests"], config
assert "separate reviewed-write surface" in " ".join(bridge_snippets["required_bridge_behavior"]), config
assert bridge_snippets["tool_manifest_ref"] == "tool_protocol_bridge.host_tool_manifest", config
managed_bridge = config["managed_tool_host_bridge"]
assert managed_bridge["format"] == "akbp-managed-tool-host-bridge-v1", config
assert managed_bridge["server_config"]["transport"] == "stdio", config
assert managed_bridge["server_config"]["knowledge_base_path"] == config["knowledge_base"]["path"], config
assert managed_bridge["safe_default_profile"] == "read_only", config
assert managed_bridge["startup_profile"] == "read_only", config
assert "akbp_session_start" in managed_bridge["tool_exposure"]["read_only_tools"], config
assert managed_bridge["tool_exposure"]["forwards_to"]["akbp_session_start"] == "akbp.session.start", config
assert "akbp.remember" in managed_bridge["tool_exposure"]["blocked_write_methods"], config
assert "approved:true" in managed_bridge["tool_exposure"]["enable_write_tools_only_when"][3], config
assert managed_bridge["preflight_requests"] == config["tool_protocol_bridge"]["host_tool_manifest"]["preflight_requests"], config
assert managed_bridge["response_requirements"]["preserve_envelope"] is True, config
assert "error.code" in managed_bridge["response_requirements"]["branch_on"], config
assert "citations" in managed_bridge["response_requirements"]["surface"], config
assert "uncited summaries" in managed_bridge["response_requirements"]["do_not_store"], config
assert "read-only startup context" in managed_bridge["fallback"], config
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
assert config["tool_protocol_bridge_snippets"]["server_process"]["env"]["AKBP_KB_PATH"] == "<AKBP_KB_PATH>", config
assert config["tool_protocol_bridge_snippets"]["host_server_template"]["toolServers"]["akbp"]["args"][3] == "<AKBP_KB_PATH>", config
assert config["multi_client_scope"]["safe_for_public_templates"] is True, config
assert config["scope_selection"]["selected_kb_path"] == "<AKBP_KB_PATH>", config
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
assert config["managed_tool_host_bridge"]["startup_profile"] == "reviewed_write", config
assert "adapter_readiness.reviewed_write_ready" in config["managed_tool_host_bridge"]["tool_exposure"]["enable_write_tools_only_when"][1], config
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
