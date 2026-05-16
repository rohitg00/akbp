import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "cli" / "akbp.py"
SERVER = ROOT / "tool-server" / "akbp_tool_server.py"


def run_cli(*args):
    return subprocess.run([sys.executable, str(CLI), *args], text=True, capture_output=True, check=True)


class AkbpCliSmokeTest(unittest.TestCase):
    def test_source_add_url_requires_http_locator(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            run_cli("--path", str(kb), "init")
            bad = subprocess.run(
                [
                    sys.executable,
                    str(CLI),
                    "--path",
                    str(kb),
                    "source",
                    "add",
                    "docs.example.com/release",
                    "--type",
                    "url",
                ],
                text=True,
                capture_output=True,
            )
            self.assertNotEqual(bad.returncode, 0)
            self.assertIn("http:// or https://", bad.stderr)

            out = run_cli(
                "--path",
                str(kb),
                "source",
                "add",
                "https://docs.example.com/release",
                "--type",
                "url",
                "--title",
                "Release docs",
            )
            source = json.loads(out.stdout)
            self.assertEqual(source["type"], "url")
            self.assertEqual(source["locator"], "https://docs.example.com/release")
            self.assertIsNone(source["hash"])

    def test_status_accepts_adapter_profile_readiness_gate(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            run_cli("--path", str(kb), "init")
            out = run_cli("--path", str(kb), "status", "--profile", "startup-context")
            status = json.loads(out.stdout)
            self.assertEqual(status["requested_profile"], "startup_context")
            self.assertTrue(status["requested_profile_ready"])
            self.assertTrue(status["adapter_readiness"]["startup_context_ready"])
            self.assertFalse(status["adapter_readiness"]["read_only_ready"])

    def test_client_config_generates_negotiated_stdio_profile(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            run_cli("--path", str(kb), "init")
            out = run_cli(
                "--path", str(kb),
                "client-config",
                "--name", "stdio-adapter-test",
                "--profile", "reviewed-writes",
                "--command", "python-module",
            )
            config = json.loads(out.stdout)
            self.assertEqual(config["transport"], "stdio-jsonl")
            self.assertEqual(config["server"]["command"], "python3")
            self.assertEqual(config["server"]["args"], ["-m", "akbp_tool_server"])
            self.assertEqual(config["knowledge_base"]["path"], str(kb.resolve()))
            self.assertEqual(config["knowledge_capability"]["type"], "durable_agent_knowledge")
            self.assertEqual(config["knowledge_capability"]["default_mode"], "read_only")
            self.assertEqual(config["knowledge_capability"]["write_mode"], "reviewed_write_only")
            self.assertIn("source_backed_claims", config["knowledge_capability"]["guarantees"])
            self.assertIn("uncited vector cache", config["knowledge_capability"]["not_a"])
            self.assertIn("approved:true", config["knowledge_capability"]["host_mapping"]["apply"])
            session_boundary = config["knowledge_capability"]["session_boundary"]
            self.assertIn("raw transcripts", session_boundary["runtime_transient_state"])
            self.assertEqual(session_boundary["promotion_method"], "akbp.session.end")
            self.assertIn("dry_run preview", session_boundary["promotion_gate"])
            self.assertIn("approved AKBP artifacts", session_boundary["trusted_durable_state"])
            descriptor = config["host_capability_descriptor"]
            self.assertEqual(descriptor["format"], "akbp-host-capability-descriptor-v1")
            self.assertEqual(descriptor["capability_type"], "durable_agent_knowledge")
            self.assertEqual(descriptor["transport"], "stdio-jsonl")
            self.assertEqual(descriptor["default_profile"], "reviewed_write")
            self.assertEqual(descriptor["safe_default_profile"], "read_only")
            self.assertEqual(descriptor["profile_contracts"]["read_only"]["write_policy"], "no_writes")
            self.assertFalse(descriptor["profile_contracts"]["read_only"]["requires_review_surface"])
            self.assertTrue(descriptor["profile_contracts"]["reviewed_write"]["requires_review_surface"])
            self.assertEqual(
                descriptor["profile_contracts"]["reviewed_write"]["write_policy"],
                "dry_run_preview_then_approved_apply",
            )
            self.assertIn("akbp.session.start", descriptor["profile_contracts"]["startup_context"]["methods"])
            self.assertEqual(
                descriptor["profile_contracts"]["startup_context"]["methods"],
                ["akbp.capabilities", "akbp.doctor", "akbp.session.start", "akbp.context"],
            )
            self.assertIn("akbp.context", descriptor["read_only_methods"])
            self.assertIn("akbp.remember", descriptor["blocked_until_review_surface"])
            self.assertIn("schemas/tool-methods.schema.json", descriptor["schema_refs"]["methods"])
            self.assertIn("requires_profiles", descriptor["host_integration_rules"][0])
            bridge_snippets = config["tool_protocol_bridge_snippets"]
            self.assertEqual(bridge_snippets["format"], "akbp-tool-protocol-bridge-snippets-v1")
            self.assertFalse(bridge_snippets["direct_host_native_server"])
            self.assertTrue(bridge_snippets["bridge_required"])
            self.assertIn("without claiming", bridge_snippets["purpose"])
            self.assertEqual(bridge_snippets["safe_default_profile"], "read_only")
            self.assertEqual(bridge_snippets["requested_profile"], "reviewed_write")
            self.assertEqual(bridge_snippets["server_process"]["transport"], "stdio-jsonl")
            self.assertEqual(bridge_snippets["server_process"]["command"], "python3")
            self.assertEqual(bridge_snippets["server_process"]["args"], ["-m", "akbp_tool_server"])
            self.assertEqual(bridge_snippets["server_process"]["env"]["AKBP_KB_PATH"], str(kb.resolve()))
            self.assertEqual(
                bridge_snippets["host_server_template"]["toolServers"]["akbp"]["command"],
                "<AKBP_TOOL_BRIDGE_COMMAND>",
            )
            self.assertEqual(
                bridge_snippets["host_server_template"]["toolServers"]["akbp"]["env"]["AKBP_KB_PATH"],
                str(kb.resolve()),
            )
            self.assertEqual(bridge_snippets["preflight_requests"][0]["method"], "akbp.capabilities")
            self.assertIn("separate reviewed-write surface", " ".join(bridge_snippets["required_bridge_behavior"]))
            self.assertEqual(bridge_snippets["tool_manifest_ref"], "tool_protocol_bridge.host_tool_manifest")
            self.assertTrue(config["runtime_requirements"]["local_first"])
            self.assertFalse(config["runtime_requirements"]["network_required"])
            self.assertFalse(config["runtime_requirements"]["cloud_account_required"])
            self.assertEqual(config["runtime_requirements"]["secrets_required"], [])
            install_surface = config["runtime_requirements"]["install_surface"]
            self.assertEqual(install_surface["runtime"], "python3")
            self.assertEqual(install_surface["external_services_required"], [])
            self.assertFalse(install_surface["docker_required"])
            self.assertIn("SQLite FTS index", install_surface["database_required"])
            self.assertFalse(install_surface["network_required_after_install"])
            self.assertEqual(install_surface["first_command"], "akbp discover")
            self.assertEqual(
                install_surface["adapter_setup_order"],
                [
                    "resolve explicit knowledge_base.path",
                    "run akbp discover",
                    "run akbp doctor --profile read-only",
                    "generate akbp client-config --profile read-only",
                    "run generated preflight_requests before exposing tools",
                ],
            )
            self.assertIn("AKBP artifacts", config["runtime_requirements"]["durable_state_owner"])
            self.assertIn("read-only bridge allowlist", config["runtime_requirements"]["tool_protocol_hosts"])
            host_profiles = {profile["host_type"]: profile for profile in config["host_install_profiles"]}
            self.assertEqual(set(host_profiles), {"terminal_agent", "editor_agent", "managed_tool_protocol_host", "existing_memory_server"})
            self.assertEqual(host_profiles["terminal_agent"]["safe_default_profile"], "read_only")
            self.assertIn("client-config --profile read-only", host_profiles["terminal_agent"]["setup_commands"][2])
            self.assertEqual(host_profiles["terminal_agent"]["first_tool"], "akbp_session_start")
            self.assertIn("approved:true", host_profiles["terminal_agent"]["enable_writes_after"])
            self.assertIn(
                "host_tool_manifest",
                " ".join(host_profiles["editor_agent"]["setup_commands"]),
            )
            self.assertEqual(host_profiles["managed_tool_protocol_host"]["safe_default_profile"], "read_only")
            self.assertEqual(host_profiles["managed_tool_protocol_host"]["first_tool"], "akbp_session_start")
            self.assertIn("read-only tools", " ".join(host_profiles["managed_tool_protocol_host"]["setup_commands"]))
            self.assertIn("separate human approval", host_profiles["managed_tool_protocol_host"]["enable_writes_after"])
            self.assertEqual(host_profiles["existing_memory_server"]["first_tool"], "akbp_context")
            self.assertIn("ephemeral cache", host_profiles["existing_memory_server"]["setup_commands"][0])
            autodetect = config["host_autodetect"]
            self.assertEqual(autodetect["format"], "akbp-host-autodetect-contract-v1")
            self.assertEqual(autodetect["safe_default"], "inventory_only")
            self.assertEqual(autodetect["selected_profile"], "reviewed_write")
            self.assertIn("supports_review_surface", autodetect["inventory_fields"])
            self.assertIn("write host config files", autodetect["blocked_probe_actions"])
            self.assertIn("show the exact host config diff", " ".join(autodetect["required_install_review"]))
            self.assertIn("read-only setup commands", autodetect["fallback"])
            managed_bridge = config["managed_tool_host_bridge"]
            self.assertEqual(managed_bridge["format"], "akbp-managed-tool-host-bridge-v1")
            self.assertEqual(managed_bridge["server_config"]["transport"], "stdio")
            self.assertEqual(managed_bridge["server_config"]["knowledge_base_path"], str(kb.resolve()))
            self.assertEqual(managed_bridge["safe_default_profile"], "read_only")
            self.assertEqual(managed_bridge["startup_profile"], "reviewed_write")
            self.assertIn("akbp_session_start", managed_bridge["tool_exposure"]["read_only_tools"])
            self.assertEqual(
                managed_bridge["tool_exposure"]["forwards_to"]["akbp_session_start"],
                "akbp.session.start",
            )
            self.assertIn("akbp.remember", managed_bridge["tool_exposure"]["blocked_write_methods"])
            self.assertIn("adapter_readiness.reviewed_write_ready", managed_bridge["tool_exposure"]["enable_write_tools_only_when"][1])
            self.assertEqual(managed_bridge["preflight_requests"], config["tool_protocol_bridge"]["host_tool_manifest"]["preflight_requests"])
            self.assertTrue(managed_bridge["response_requirements"]["preserve_envelope"])
            self.assertIn("error.code", managed_bridge["response_requirements"]["branch_on"])
            self.assertIn("citations", managed_bridge["response_requirements"]["surface"])
            self.assertIn("uncited summaries", managed_bridge["response_requirements"]["do_not_store"])
            self.assertIn("read-only startup context", managed_bridge["fallback"])
            memory_bridge = config["memory_server_bridge"]
            self.assertEqual(memory_bridge["safe_default"], "read_only_substrate")
            self.assertEqual(memory_bridge["bridge_role"], "transport_and_policy_glue_only")
            self.assertIn("AKBP markdown and JSONL artifacts", memory_bridge["durable_state_owner"])
            modes = {mode["mode"]: mode for mode in memory_bridge["integration_modes"]}
            self.assertIn("runtime_cache_plus_akbp", modes)
            self.assertIn("tool_protocol_bridge", modes)
            self.assertIn("migration_review", modes)
            self.assertIn("dry_run preview", modes["runtime_cache_plus_akbp"]["required_gate"])
            self.assertIn("host_tool_manifest", modes["tool_protocol_bridge"]["akbp_boundary"])
            self.assertIn("import-check", modes["migration_review"]["required_gate"])
            self.assertIn("error.code", " ".join(memory_bridge["must_preserve"]))
            self.assertIn("opaque format", " ".join(memory_bridge["disable_or_warn_when"]))
            external_promotion = memory_bridge["external_memory_promotion"]
            self.assertEqual(external_promotion["format"], "akbp-external-memory-promotion-v1")
            self.assertEqual(external_promotion["safe_default"], "import_check_before_apply")
            self.assertEqual(external_promotion["candidate_record_shape"]["source"]["kind"], "akbp_source_id|file|url|citation")
            triage = external_promotion["promotion_triage"]
            self.assertEqual(triage["format"], "akbp-memory-promotion-triage-v1")
            self.assertIn("deterministic decision map", triage["purpose"])
            triage_classes = [decision["class"] for decision in triage["decisions"]]
            self.assertEqual(
                triage_classes,
                ["runtime_scratch", "ephemeral_hint", "candidate_durable_claim", "blocked_private_or_secret"],
            )
            self.assertIn("source_reference_status", triage["required_adapter_output"])
            self.assertIn("classification is missing", triage["fail_closed_when"])
            self.assertIn("missing_source", external_promotion["reject_reasons"])
            self.assertIn("source.kind", external_promotion["required_review_fields"])
            promotion_steps = {step["step"]: step for step in external_promotion["promotion_sequence"]}
            self.assertIn("check_import", promotion_steps)
            self.assertIn("import-check", promotion_steps["check_import"]["command"])
            self.assertIn("approved:true", promotion_steps["approved_apply"]["command"])
            self.assertEqual(memory_bridge["promotion_contract_ref"], "memory_server_bridge.external_memory_promotion")
            promotion = memory_bridge["promotion_contract"]
            self.assertIn("reviewed durable knowledge", promotion["purpose"])
            self.assertIn("source-backed facts", promotion["candidate_records"])
            self.assertIn("uncited summaries", promotion["reject_records"])
            self.assertIn("source id or citation", promotion["required_review_fields"])
            self.assertIn("akbp.import_check", " ".join(promotion["preflight_requests"]))
            self.assertIn("approved:true", promotion["apply_rule"])
            self.assertIn("read-only", promotion["fallback"])
            landscape = config["memory_landscape_fit"]
            self.assertEqual(landscape["format"], "akbp-memory-landscape-fit-v1")
            self.assertIn("tool-protocol memory servers", landscape["purpose"])
            self.assertIn("one-command local setup for coding-agent memory", landscape["observed_user_pull"])
            self.assertIn("no-Docker and no-API-key local memory installs", landscape["observed_user_pull"])
            self.assertIn("shared memory across tool-protocol-compatible tools", landscape["observed_user_pull"])
            self.assertIn("reviewed durable project knowledge", landscape["akbp_should_own"])
            self.assertIn("cited startup context", landscape["akbp_should_own"])
            self.assertIn("opaque chat-memory databases", landscape["akbp_should_not_own"])
            self.assertIn("uncited summaries promoted as project facts", landscape["akbp_should_not_own"])
            self.assertIn("portable trust layer", landscape["installer_positioning"])
            self.assertIn("dry_run:true", " ".join(landscape["comparison_checks"]))
            self.assertIn("export-check", " ".join(landscape["comparison_checks"]))
            self.assertIn("branch or worktree-specific handoffs", " ".join(landscape["comparison_checks"]))
            claim_audit = {item["claim"]: item for item in landscape["feature_claim_audit"]}
            self.assertIn("semantic, graph, or hierarchical memory improves recall", claim_audit)
            self.assertIn("memory reduces context-window cost", claim_audit)
            self.assertIn("multiple agents share one project memory", claim_audit)
            self.assertIn("branch-aware handoffs prevent stale coding-agent context", claim_audit)
            self.assertIn("local-first memory is safe by default", claim_audit)
            self.assertIn("runnable search or benchmark proof", claim_audit["semantic, graph, or hierarchical memory improves recall"]["akbp_check"])
            self.assertIn("result.context.budget", claim_audit["memory reduces context-window cost"]["evidence"])
            self.assertIn("single selected knowledge_base.path", claim_audit["multiple agents share one project memory"]["akbp_check"])
            self.assertIn("worktree path", claim_audit["branch-aware handoffs prevent stale coding-agent context"]["akbp_check"])
            self.assertIn("approval_required", claim_audit["local-first memory is safe by default"]["evidence"])
            branch_scope = landscape["git_native_handoff_branch_scope"]
            self.assertEqual(branch_scope["format"], "akbp-git-native-handoff-branch-scope-v1")
            self.assertIn("feature branches", branch_scope["purpose"])
            self.assertIn("current branch name when available", branch_scope["adapter_must_capture"])
            self.assertIn("commit sha or dirty-worktree marker", branch_scope["adapter_must_capture"])
            self.assertIn("Git, not AKBP memory", branch_scope["akbp_boundary"][1])
            self.assertIn("akbp.session.start", branch_scope["preflight"][0])
            self.assertIn("uncited transcript summaries", branch_scope["fail_closed_when"][1])
            self.assertIn("repository-wide cited context", branch_scope["fallback"])
            friction = landscape["install_friction_checks"]
            self.assertIn("without Docker", friction[0]["question"])
            self.assertEqual(friction[0]["verify_with"], "ten_minute_proof.setup_claims")
            self.assertIn("multi_client_scope.shared_kb_path", friction[1]["akbp_expectation"])
            self.assertIn("structured-output harness", friction[2]["akbp_expectation"])
            self.assertIn("harness_adoption_fit.minimum_gate", friction[2]["verify_with"])
            local_probe = landscape["local_first_adoption_probe"]
            self.assertEqual(local_probe["format"], "akbp-local-first-adoption-probe-v1")
            self.assertTrue(local_probe["run_before_positioning_claims"])
            self.assertIn("akbp discover", local_probe["commands"])
            self.assertIn("akbp doctor --profile read-only", local_probe["commands"])
            self.assertIn("./examples/structured-output-harness/run.sh", local_probe["commands"])
            self.assertIn("no Docker", local_probe["must_prove"][0])
            self.assertIn("knowledge_base.path", local_probe["must_prove"][1])
            self.assertIn("approval_required", local_probe["must_prove"][3])
            self.assertIn("opaque sidecar database", local_probe["fail_closed_when"][1])
            self.assertIn("read-only startup context", local_probe["fallback"])
            self.assertIn("ephemeral hint source", landscape["fallback"])
            harness_fit = config["harness_adoption_fit"]
            self.assertEqual(harness_fit["format"], "akbp-harness-adoption-fit-v1")
            self.assertIn("structured-output", harness_fit["purpose"])
            self.assertIn("structured outputs", harness_fit["observed_user_pull"][0])
            self.assertIn("negotiate capabilities", " ".join(harness_fit["akbp_harness_role"]))
            self.assertEqual(harness_fit["minimum_gate"]["command"], "./examples/structured-output-harness/run.sh")
            self.assertIn("AKBP structured output harness example passed", harness_fit["minimum_gate"]["success_markers"])
            self.assertIn("planning from recalled AKBP context", harness_fit["minimum_gate"]["must_pass_before"])
            self.assertIn("error.code", harness_fit["minimum_gate"]["required_fields"])
            self.assertIn("verified memory harness boundary", harness_fit["installer_positioning"])
            self.assertIn("read-only", harness_fit["fallback"])
            interop = config["native_memory_interop"]
            self.assertEqual(interop["format"], "akbp-native-memory-interop-v1")
            self.assertEqual(interop["safe_default"], "akbp_as_cited_source_of_truth")
            self.assertIn("product-native memory", interop["purpose"])
            self.assertIn("cited AKBP startup context", interop["read_order"][0])
            self.assertIn("ephemeral hints", interop["read_order"][1])
            self.assertIn("dry_run:true", " ".join(interop["write_order"]))
            self.assertIn("approved:true", " ".join(interop["write_order"]))
            self.assertEqual(interop["conflict_policy"]["prefer"], "active AKBP claims with citations and verified sources")
            self.assertIn("supersede or contradict", interop["conflict_policy"]["when_native_memory_disagrees"])
            self.assertIn("no source or citation", " ".join(interop["reject_promotion_when"]))
            self.assertIn("read-only", interop["fallback"])
            compaction = config["context_compaction_recovery"]
            self.assertEqual(compaction["format"], "akbp-context-compaction-recovery-v1")
            self.assertIn("conversation compaction", compaction["purpose"])
            self.assertIn("context loss", compaction["research_signal"])
            self.assertIn("the host compacted or summarized the conversation", compaction["trigger_when"])
            self.assertEqual(compaction["recovery_sequence"][0]["request"], "session_start")
            self.assertIn("adapter_prompt_contract.context_use_report", compaction["recovery_sequence"][1]["request"])
            self.assertIn("startup_trust_gate", compaction["recovery_sequence"][2]["request"])
            self.assertIn("uncited chat summaries", compaction["do_not_recover_from"])
            self.assertIn("fresh session", compaction["fallback"])
            multi_client = config["multi_client_scope"]
            self.assertIn("share one reviewed knowledge base", multi_client["purpose"])
            self.assertEqual(multi_client["shared_kb_path"], str(kb.resolve()))
            self.assertEqual(multi_client["client_identity_field"], "startup.params.client")
            self.assertEqual(multi_client["default_mode"], "read_only")
            self.assertIn("same selected knowledge_base.path", multi_client["scope_rule"])
            self.assertIn("Runtime scratchpads", multi_client["isolation_rule"])
            self.assertIn("supersede or contradict", multi_client["conflict_policy"])
            self.assertIn("append audit records", multi_client["audit_policy"])
            self.assertFalse(multi_client["safe_for_public_templates"])
            first_run = config["first_run_sequence"]
            self.assertIn("ordered setup path", first_run["purpose"])
            self.assertIn("keep the integration read-only", first_run["stop_policy"])
            self.assertEqual(
                [step["step"] for step in first_run["steps"]],
                [
                    "resolve_knowledge_base",
                    "negotiate_capabilities",
                    "check_adapter_readiness",
                    "retrieve_cited_startup_context",
                    "enable_writes_only_after_review_surface",
                ],
            )
            self.assertTrue(first_run["steps"][0]["required"])
            self.assertEqual(first_run["steps"][0]["expect"]["knowledge_base.path"], str(kb.resolve()))
            self.assertEqual(first_run["steps"][1]["request_id"], "capabilities-1")
            self.assertTrue(first_run["steps"][1]["expect"]["result.features.method_param_schemas"])
            self.assertEqual(first_run["steps"][2]["request_id"], "doctor-1")
            self.assertEqual(first_run["steps"][2]["expect"]["result.requested_profile"], "reviewed_write")
            self.assertTrue(first_run["steps"][2]["expect"]["result.requested_profile_ready"])
            self.assertTrue(first_run["steps"][2]["expect"]["result.adapter_readiness.reviewed_write_ready"])
            self.assertEqual(first_run["steps"][3]["request_id"], "session-start-1")
            self.assertEqual(first_run["steps"][3]["expect"]["result.context.budget.max_chars"], 4000)
            self.assertTrue(first_run["steps"][4]["required"])
            self.assertTrue(first_run["steps"][4]["expect"]["approval_outside_model_tool_call"])
            repair = config["structured_output_repair"]
            self.assertEqual(repair["format"], "akbp-structured-output-repair-v1")
            retryable_codes = {entry["error_code"] for entry in repair["retryable_after_local_fix"]}
            self.assertEqual(retryable_codes, {"invalid_json", "invalid_request", "invalid_params", "unknown_method"})
            self.assertEqual(repair["max_local_repair_attempts"], 1)
            self.assertIn("params fingerprint", repair["repair_attempt_scope"])
            self.assertIn("params_schema", repair["retryable_after_local_fix"][2]["fix"])
            self.assertIn("approval_required", repair["never_auto_repair"])
            self.assertIn("startup context without citations", repair["never_auto_repair"])
            self.assertIn("dry_run:true", repair["write_retry_rule"])
            self.assertIn("repair budget is exhausted", repair["exhausted_retry_action"])
            self.assertIn("read-only", repair["adapter_action"])
            ten_minute = config["ten_minute_proof"]
            self.assertEqual(ten_minute["format"], "akbp-ten-minute-proof-v1")
            self.assertIn("local, cited, review-gated, portable memory", ten_minute["user_value_gap"])
            self.assertTrue(ten_minute["setup_claims"]["local_first"])
            self.assertFalse(ten_minute["setup_claims"]["requires_docker"])
            self.assertFalse(ten_minute["setup_claims"]["requires_cloud_account"])
            proof_names = {step["name"] for step in ten_minute["proof_steps"]}
            self.assertIn("retrieve_cited_context", proof_names)
            self.assertIn("block_unapproved_apply", proof_names)
            self.assertIn("validate_adapter_response_contract", proof_names)
            self.assertIn("export_checked_bundle", proof_names)
            self.assertIn("adapter_contract_harness", json.dumps(ten_minute["proof_steps"]))
            self.assertIn("approval_required", " ".join(ten_minute["success_markers"]))
            self.assertIn("adapter_contract_harness", " ".join(ten_minute["success_markers"]))
            self.assertIn("read-only", ten_minute["fallback"])
            inherited_intake = config["inherited_repo_intake"]
            self.assertEqual(inherited_intake["format"], "akbp-inherited-repo-intake-v1")
            self.assertEqual(inherited_intake["safe_default"], "read_only_until_sources_verify")
            self.assertIn("source verify --fail-on-issue", json.dumps(inherited_intake["preflight_sequence"]))
            self.assertIn("changed or missing source evidence", inherited_intake["trust_gate"]["fail_closed_on"])
            self.assertEqual(inherited_intake["example"], "./examples/inherited-repo-intake/run.sh")
            self.assertEqual(config["startup"]["id"], "capabilities-1")
            self.assertEqual(config["startup"]["method"], "akbp.capabilities")
            self.assertEqual(config["startup"]["path"], str(kb.resolve()))
            self.assertEqual(config["startup"]["params"]["client"], "stdio-adapter-test")
            self.assertIn("capability_negotiation", config["startup"]["params"]["requires"])
            self.assertIn("bounded_context", config["startup"]["params"]["requires"])
            self.assertEqual(config["startup"]["params"]["requires_profiles"], ["reviewed_write"])
            self.assertEqual(config["session_start"]["id"], "session-start-1")
            self.assertEqual(config["session_start"]["method"], "akbp.session.start")
            self.assertEqual(config["session_start"]["path"], str(kb.resolve()))
            self.assertEqual(config["session_start"]["params"]["max_chars"], 4000)
            self.assertEqual(config["session_start"]["params"]["min_items"], 1)
            self.assertTrue(config["session_start"]["params"]["require_citations"])
            self.assertTrue(config["session_start"]["params"]["fail_on_warnings"])
            self.assertEqual(config["response_contract"]["envelope"]["required"], ["id", "ok", "result", "error"])
            self.assertIn("Branch on error.code", config["response_contract"]["error_rules"][0])
            self.assertEqual(config["response_contract"]["schemas"]["response"], "schemas/tool-response.schema.json")
            self.assertEqual(config["health_check"]["id"], "doctor-1")
            self.assertEqual(config["health_check"]["path"], str(kb.resolve()))
            self.assertEqual(config["health_check"]["params"]["profile"], "reviewed_write")
            self.assertEqual(config["health_check"]["requested_profile_ready_field"], "requested_profile_ready")
            self.assertEqual(config["health_check"]["recommended_profile_field"], "adapter_readiness.recommended_profile")
            self.assertEqual(config["health_check"]["security_posture_field"], "security_posture")
            self.assertEqual(config["tool_protocol_bridge"]["mode"], "reviewed_write")
            forward_tools = config["tool_protocol_bridge"]["forward_tools"]
            self.assertEqual(forward_tools[0]["tool"], "akbp_capabilities")
            self.assertEqual(forward_tools[0]["method"], "akbp.capabilities")
            self.assertEqual(forward_tools[0]["mode"], "read_only")
            self.assertIn("Discover supported AKBP methods", forward_tools[0]["description"])
            self.assertEqual(forward_tools[0]["safety"]["writes"], False)
            self.assertEqual(forward_tools[0]["safety"]["requires_review_surface"], False)
            self.assertEqual(forward_tools[0]["safety"]["approval"], "not_applicable")
            self.assertTrue(forward_tools[0]["params_schema"].endswith("#/$defs/akbp.capabilities.params"))
            self.assertIn("result.negotiation", forward_tools[0]["surface_fields"])
            self.assertEqual(
                [tool["method"] for tool in forward_tools],
                config["tool_protocol_bridge"]["read_only_allowlist"],
            )
            manifest = config["tool_protocol_bridge"]["host_tool_manifest"]
            self.assertEqual(manifest["format"], "akbp-tool-host-manifest-v1")
            self.assertEqual(manifest["transport"], "stdio-jsonl")
            self.assertEqual(manifest["server"], config["server"])
            self.assertEqual(manifest["knowledge_base_path"], str(kb.resolve()))
            self.assertEqual(manifest["default_mode"], "read_only")
            self.assertIn("second memory format", manifest["purpose"])
            self.assertIn("separate reviewed-write surface", manifest["approval_boundary"])
            self.assertEqual(manifest["tool_schema_budget"]["format"], "akbp-tool-schema-budget-v1")
            self.assertEqual(manifest["tool_schema_budget"]["selected_profile"], "reviewed_write")
            self.assertEqual(manifest["tool_schema_budget"]["exposed_method_count"], len(forward_tools))
            self.assertEqual(manifest["tool_schema_budget"]["max_exposed_methods_for_profile"], 8)
            self.assertTrue(manifest["tool_schema_budget"]["within_budget"])
            self.assertEqual(manifest["tool_schema_budget"]["budget_check"], "pass")
            self.assertEqual(manifest["tool_schema_budget"]["overflow_methods"], [])
            budget_gate = manifest["tool_schema_budget"]["preflight_gate"]
            self.assertEqual(budget_gate["format"], "akbp-tool-schema-budget-gate-v1")
            self.assertTrue(budget_gate["required_before_host_tool_exposure"])
            self.assertIn("within_budget is true", budget_gate["pass_conditions"])
            self.assertIn("overflow_methods is empty", budget_gate["pass_conditions"])
            self.assertIn("blocked_until_needed methods are not exposed", " ".join(budget_gate["pass_conditions"]))
            self.assertIn("exposed_method_count", budget_gate["required_adapter_output"])
            self.assertIn("Do not expose host tools", budget_gate["fail_closed_action"])
            self.assertIn("akbp.remember", manifest["tool_schema_budget"]["blocked_until_needed"])
            self.assertIn("every exposed tool schema consumes context", manifest["tool_schema_budget"]["research_signal"])
            self.assertEqual(
                [tool["forwards_to"] for tool in manifest["tools"]],
                config["tool_protocol_bridge"]["read_only_allowlist"],
            )
            self.assertEqual(manifest["tools"][0]["name"], "akbp_capabilities")
            self.assertEqual(manifest["tools"][0]["description"], forward_tools[0]["description"])
            self.assertEqual(manifest["tools"][0]["safety"], forward_tools[0]["safety"])
            self.assertEqual(manifest["tools"][0]["input_schema"], forward_tools[0]["params_schema"])
            self.assertEqual(manifest["tools"][0]["preserve_response_fields"], forward_tools[0]["surface_fields"])
            self.assertEqual(
                [request["id"] for request in manifest["preflight_requests"]],
                ["capabilities-1", "doctor-1", "session-start-1"],
            )
            self.assertEqual(manifest["preflight_requests"][0]["method"], "akbp.capabilities")
            self.assertEqual(manifest["preflight_requests"][0]["path"], str(kb.resolve()))
            self.assertEqual(manifest["preflight_requests"][0]["params"]["requires_profiles"], ["reviewed_write"])
            self.assertTrue(manifest["preflight_requests"][0]["expect"]["result.negotiation.satisfied"])
            self.assertEqual(manifest["preflight_requests"][1]["method"], "akbp.doctor")
            self.assertEqual(manifest["preflight_requests"][1]["params"]["profile"], "reviewed_write")
            self.assertEqual(manifest["preflight_requests"][1]["expect"]["result.requested_profile"], "reviewed_write")
            self.assertTrue(manifest["preflight_requests"][1]["expect"]["result.requested_profile_ready"])
            self.assertTrue(manifest["preflight_requests"][1]["expect"]["result.adapter_readiness.reviewed_write_ready"])
            self.assertEqual(manifest["preflight_requests"][2]["method"], "akbp.session.start")
            self.assertEqual(manifest["preflight_requests"][2]["params"]["max_chars"], 4000)
            self.assertEqual(manifest["preflight_requests"][2]["params"]["min_items"], 1)
            self.assertTrue(manifest["preflight_requests"][2]["params"]["require_citations"])
            self.assertTrue(manifest["preflight_requests"][2]["params"]["fail_on_warnings"])
            self.assertEqual(manifest["preflight_requests"][2]["expect"]["result.quality.minimum_items"], 1)
            self.assertTrue(manifest["preflight_requests"][2]["expect"]["result.quality.require_citations"])
            self.assertTrue(manifest["preflight_requests"][2]["expect"]["result.quality.fail_on_warnings"])
            preflight_replay = config["tool_protocol_bridge"]["preflight_replay"]
            self.assertEqual(preflight_replay["format"], "akbp-preflight-replay-v1")
            self.assertEqual(preflight_replay["request_count"], 3)
            replay_lines = [json.loads(line) for line in preflight_replay["request_jsonl"].splitlines()]
            self.assertEqual([line["id"] for line in replay_lines], ["capabilities-1", "doctor-1", "session-start-1"])
            self.assertEqual(replay_lines[0]["method"], "akbp.capabilities")
            self.assertNotIn("expect", replay_lines[0])
            self.assertEqual(replay_lines[0]["path"], str(kb.resolve()))
            self.assertTrue(replay_lines[2]["params"]["require_citations"])
            self.assertIn("result.context.items[].citations", preflight_replay["must_preserve"])
            self.assertIn("Do not expose host tools", preflight_replay["on_failure"])
            self.assertEqual(config["tool_protocol_bridge_snippets"]["preflight_replay"], preflight_replay)
            client_manifest = config["tool_protocol_bridge"]["client_tool_manifest"]
            self.assertEqual(client_manifest["format"], "akbp-client-tool-manifest-v1")
            self.assertEqual(client_manifest["server"], {"name": "stdio-adapter-test", **config["server"]})
            self.assertEqual(client_manifest["knowledge_base_path"], str(kb.resolve()))
            self.assertEqual(client_manifest["default_mode"], "read_only")
            self.assertEqual(client_manifest["transport_adapter"], "stdio-jsonl-to-host-tools")
            self.assertEqual(client_manifest["tool_schema_budget"], manifest["tool_schema_budget"])
            self.assertTrue(client_manifest["response_contract"]["preserve_envelope"])
            self.assertEqual(client_manifest["response_contract"]["branch_on"], "error.code")
            self.assertTrue(client_manifest["response_contract"]["surface_citations"])
            self.assertEqual(
                [tool["akbp_method"] for tool in client_manifest["tools"]],
                config["tool_protocol_bridge"]["read_only_allowlist"],
            )
            self.assertEqual(client_manifest["tools"][0]["name"], "akbp_capabilities")
            self.assertEqual(client_manifest["tools"][0]["description"], forward_tools[0]["description"])
            self.assertEqual(client_manifest["tools"][0]["safety"], forward_tools[0]["safety"])
            self.assertEqual(client_manifest["tools"][0]["input_schema_ref"], forward_tools[0]["params_schema"])
            self.assertIn("akbp.remember", client_manifest["blocked_write_methods"])
            self.assertIn("dry-run previews", client_manifest["approval_boundary"])
            self.assertEqual(client_manifest["preflight_requests"], manifest["preflight_requests"])
            self.assertEqual(client_manifest["preflight_replay"], preflight_replay)
            self.assertIn("result.context.items", forward_tools[2]["surface_fields"])
            self.assertIn("akbp.session.start", config["tool_protocol_bridge"]["read_only_allowlist"])
            self.assertEqual(
                config["tool_protocol_bridge"]["tool_schema_budget"]["exposed_methods"],
                config["tool_protocol_bridge"]["read_only_allowlist"],
            )
            self.assertIn("akbp.remember", config["tool_protocol_bridge"]["blocked_write_methods"])
            self.assertIn("akbp.source.add", config["tool_protocol_bridge"]["blocked_write_methods"])
            self.assertIn("akbp.index", config["tool_protocol_bridge"]["blocked_write_methods"])
            self.assertEqual(config["tool_protocol_bridge"]["reviewed_write_tools"][0]["required_flags"], {"dry_run": True})
            reviewed_tools = {tool["tool"]: tool for tool in config["tool_protocol_bridge"]["reviewed_write_tools"]}
            self.assertEqual(reviewed_tools["akbp_ingest_preview"]["method"], "akbp.ingest")
            self.assertEqual(reviewed_tools["akbp_ingest_preview"]["required_flags"], {"dry_run": True})
            self.assertEqual(reviewed_tools["akbp_apply_reviewed"]["required_flags"], {"approved": True})
            self.assertEqual(reviewed_tools["akbp_index_apply"]["method"], "akbp.index")
            self.assertEqual(reviewed_tools["akbp_index_apply"]["required_flags"], {"approved": True})
            self.assertIn("exact reviewed method", config["tool_protocol_bridge"]["apply_rule"])
            self.assertEqual([step["run"] for step in config["verification"]], ["startup", "health_check", "session_start"])
            self.assertTrue(config["verification"][0]["expect"]["result.negotiation.satisfied"])
            self.assertTrue(config["verification"][1]["expect"]["result.adapter_readiness.reviewed_write_ready"])
            self.assertEqual(
                config["verification"][1]["expect"]["result.security_posture.write_boundary"],
                "dry_run_preview_then_approved_apply",
            )
            self.assertEqual(config["verification"][1]["expect"]["result.summary.errors"], 0)
            self.assertEqual(config["verification"][2]["expect"]["result.context.items"], "array")
            self.assertEqual(config["verification"][2]["expect"]["result.context.budget.max_chars"], 4000)
            self.assertEqual(config["verification"][2]["expect"]["result.quality.minimum_items"], 1)
            self.assertTrue(config["verification"][2]["expect"]["result.quality.require_citations"])
            self.assertTrue(config["verification"][2]["expect"]["result.quality.fail_on_warnings"])
            self.assertEqual(config["quality_gates"]["startup_context"]["minimum_items"], 1)
            self.assertTrue(config["quality_gates"]["startup_context"]["require_citations"])
            self.assertEqual(config["quality_gates"]["startup_context"]["max_chars"], 4000)
            self.assertTrue(config["quality_gates"]["startup_context"]["require_budget"])
            self.assertTrue(config["quality_gates"]["startup_context"]["fail_on_warnings"])
            self.assertIn("bounded cited context", config["quality_gates"]["startup_context"]["budget_policy"])
            self.assertIn("session-start-harness", config["quality_gates"]["startup_context"]["recommended_harness"])
            self.assertTrue(config["quality_gates"]["reviewed_writes"]["required_for_apply"])
            self.assertIn("apply_instruction", config["quality_gates"]["reviewed_writes"]["preview_fields"])
            self.assertIn("stale or unaudited memory", config["maintenance"]["purpose"])
            self.assertEqual(config["maintenance"]["checks"][0]["method"], "akbp.source.verify")
            self.assertEqual(config["maintenance"]["checks"][0]["params"]["source_id"], "<AKBP_SOURCE_ID>")
            self.assertEqual(config["maintenance"]["checks"][0]["expected"]["result.counts.changed"], 0)
            self.assertEqual(config["maintenance"]["checks"][1]["method"], "akbp.doctor")
            self.assertTrue(config["maintenance"]["checks"][1]["expected"]["result.adapter_readiness.reviewed_write_ready"])
            self.assertEqual(config["maintenance"]["checks"][2]["method"], "akbp.export_check")
            self.assertEqual(config["maintenance"]["checks"][2]["params"]["file"], "<AKBP_EXPORT_BUNDLE>")
            self.assertIn("unsupported workflow profiles", config["maintenance"]["warning_policy"])
            self.assertEqual(config["safety"]["write_policy"], "dry_run_then_approved")
            self.assertEqual(
                config["safety"]["host_trust_boundary"]["hosted_autonomous_tools"],
                "use_read_only_unless_a_separate_human_approval_step_exists",
            )
            self.assertTrue(config["safety"]["require_human_review_surface"])
            self.assertTrue(config["safety"]["never_auto_apply_session_end"])

            caps = subprocess.run(
                [sys.executable, str(SERVER)],
                input=json.dumps(config["startup"]) + "\n",
                text=True,
                capture_output=True,
                check=True,
            )
            negotiated = json.loads(caps.stdout)
            self.assertTrue(negotiated["result"]["negotiation"]["satisfied"])
            self.assertEqual(negotiated["result"]["negotiation"]["supported_profiles"], ["reviewed_write"])
            contracts = negotiated["result"]["profile_contracts"]
            self.assertEqual(contracts["read_only"]["write_policy"], "no_writes")
            self.assertEqual(contracts["read_only"]["ready_field"], "adapter_readiness.read_only_ready")
            self.assertTrue(contracts["reviewed_write"]["requires_review_surface"])
            self.assertEqual(contracts["reviewed_write"]["write_policy"], "dry_run_preview_then_approved_apply")
            self.assertEqual(contracts["startup_context"]["ready_field"], "adapter_readiness.startup_context_ready")

            read_only = json.loads(run_cli("--path", str(kb), "client-config").stdout)
            self.assertEqual(read_only["startup"]["params"]["requires_profiles"], ["read_only"])
            self.assertEqual(read_only["profile_selection"]["format"], "akbp-adapter-profile-selection-v1")
            self.assertEqual(read_only["profile_selection"]["safe_default"], "read_only")
            self.assertEqual(read_only["tool_schema_budget"]["safe_default"], "publish_read_only_allowlist")
            self.assertEqual(read_only["tool_schema_budget"]["selected_profile"], "read_only")
            self.assertEqual(read_only["tool_schema_budget"]["max_exposed_methods_for_profile"], 8)
            self.assertTrue(read_only["tool_schema_budget"]["within_budget"])
            self.assertEqual(
                read_only["tool_schema_budget"]["preflight_gate"]["format"],
                "akbp-tool-schema-budget-gate-v1",
            )
            self.assertIn("akbp.capabilities", read_only["tool_schema_budget"]["exposed_methods"])
            self.assertIn("akbp.session.end", read_only["tool_schema_budget"]["blocked_until_needed"])
            profile_names = [profile["profile"] for profile in read_only["profile_selection"]["profiles"]]
            self.assertEqual(profile_names, ["startup_context", "read_only", "reviewed_write"])
            reviewed_profile = read_only["profile_selection"]["profiles"][2]
            self.assertIn("approved:true", " ".join(reviewed_profile["required_preflight"]))
            self.assertIn("read-only", read_only["profile_selection"]["fallback"])
            self.assertEqual(read_only["host_capability_descriptor"]["default_profile"], "read_only")
            memory_capability = read_only["host_capability_descriptor"]["tool_protocol_memory_capability"]
            self.assertEqual(memory_capability["format"], "akbp-tool-protocol-memory-capability-v1")
            self.assertIn("project_knowledge", memory_capability["candidate_labels"])
            self.assertIn("startup recall returns citations", " ".join(memory_capability["required_semantics"]))
            self.assertIn("approved:true", " ".join(memory_capability["required_semantics"]))
            self.assertIn("automatic background memory", memory_capability["do_not_advertise_as"])
            self.assertIn("read-only startup context", memory_capability["fallback"])
            self.assertNotIn("write_apply_requires_approval", read_only["startup"]["params"]["requires"])
            self.assertFalse(read_only["knowledge_base"]["portable_template"])
            self.assertEqual(read_only["response_contract"]["envelope"]["ok"], "boolean")
            self.assertEqual(read_only["tool_protocol_bridge"]["mode"], "read_only")
            self.assertIn("akbp.import_check", read_only["tool_protocol_bridge"]["read_only_allowlist"])
            self.assertEqual(read_only["verification"][1]["run"], "health_check")
            self.assertEqual(read_only["health_check"]["params"]["profile"], "read_only")
            self.assertEqual(read_only["verification"][1]["expect"]["result.requested_profile"], "read_only")
            client_intake = read_only["memory_server_bridge"]["promotion_contract"]["intake_classification"]
            self.assertEqual(client_intake["format"], "akbp-memory-intake-classification-v1")
            self.assertIn("runtime_scratch", [item["class"] for item in client_intake["classes"]])
            self.assertIn("candidate_durable_claim", [item["class"] for item in client_intake["classes"]])
            self.assertIn("source kind", client_intake["minimum_fields_before_candidate"])
            self.assertIn("import-check", read_only["memory_server_bridge"]["external_memory_promotion"]["promotion_sequence"][1]["command"])
            self.assertTrue(read_only["verification"][1]["expect"]["result.requested_profile_ready"])
            self.assertFalse(read_only["quality_gates"]["reviewed_writes"]["required_for_apply"])
            self.assertFalse(read_only["first_run_sequence"]["steps"][4]["required"])
            self.assertTrue(read_only["adapter_contract_harness"]["recommended"])
            self.assertEqual(read_only["adapter_contract_harness"]["command"], "./examples/structured-output-harness/run.sh")
            self.assertIn(
                "prompt and repair contract harness ok",
                read_only["adapter_contract_harness"]["success_markers"],
            )
            self.assertIn(
                "budget fail-closed contract ok",
                read_only["adapter_contract_harness"]["success_markers"],
            )
            self.assertIn(
                "context-use report contract ok",
                read_only["adapter_contract_harness"]["success_markers"],
            )
            self.assertIn("context-use reports", " ".join(read_only["adapter_contract_harness"]["proves"]))
            self.assertIn("approval_required", " ".join(read_only["adapter_contract_harness"]["proves"]))
            self.assertIn("read-only", read_only["adapter_contract_harness"]["stop_policy"])
            context_efficiency = read_only["memory_landscape_fit"]["context_efficiency_claim_gate"]
            self.assertEqual(context_efficiency["format"], "akbp-context-efficiency-claim-gate-v1")
            self.assertIn("token savings", context_efficiency["run_before_claiming"])
            self.assertEqual(context_efficiency["required_request"]["method"], "akbp.session.start")
            self.assertEqual(context_efficiency["required_request"]["params"]["max_chars"], 4000)
            self.assertTrue(context_efficiency["required_request"]["params"]["require_citations"])
            self.assertIn("result.context.budget.original_summary_chars", context_efficiency["must_preserve"])
            self.assertIn("trusted items keep citations", " ".join(context_efficiency["pass_when"]))
            self.assertIn("citations disappear", " ".join(context_efficiency["fail_closed_when"]))
            prompt_contract = read_only["adapter_prompt_contract"]
            self.assertEqual(prompt_contract["format"], "akbp-adapter-prompt-contract-v1")
            self.assertEqual(prompt_contract["profile"], "read_only")
            self.assertEqual(prompt_contract["startup_request"]["method"], "akbp.session.start")
            self.assertEqual(prompt_contract["startup_request"]["path"], str(kb.resolve()))
            self.assertEqual(prompt_contract["startup_request"]["params"]["max_chars"], 4000)
            self.assertEqual(prompt_contract["startup_request"]["params"]["min_items"], 1)
            self.assertTrue(prompt_contract["startup_request"]["params"]["require_citations"])
            self.assertTrue(prompt_contract["startup_request"]["params"]["fail_on_warnings"])
            self.assertTrue(prompt_contract["planning_gate"]["required_before_planning"])
            self.assertIn("do not invent prior decisions", prompt_contract["planning_gate"]["fallback"])
            self.assertIn("source ids", " ".join(prompt_contract["system_rules"]))
            trust_gate = prompt_contract["startup_trust_gate"]
            self.assertEqual(trust_gate["format"], "akbp-startup-trust-gate-v1")
            self.assertTrue(trust_gate["required_before_planning"])
            self.assertEqual(trust_gate["trust_conditions"]["minimum_items"], 1)
            self.assertTrue(trust_gate["trust_conditions"]["require_citations"])
            self.assertTrue(trust_gate["trust_conditions"]["require_budget"])
            self.assertEqual(trust_gate["trust_conditions"]["max_chars"], 4000)
            self.assertFalse(trust_gate["trust_conditions"]["warnings_allowed"])
            self.assertIn("result.context.items is empty", trust_gate["fail_closed_on"])
            self.assertIn("fail_on_warnings", " ".join(trust_gate["fail_closed_on"]))
            self.assertIn("budget.truncated", " ".join(trust_gate["fail_closed_on"]))
            self.assertIn("Continue without recalled AKBP memory", trust_gate["fallback_action"])
            context_use = prompt_contract["context_use_report"]
            self.assertEqual(context_use["format"], "akbp-context-use-report-v1")
            self.assertIn("memory-assisted planning", context_use["purpose"])
            self.assertIn("before any plan", context_use["emit_when"])
            self.assertEqual(
                context_use["required_fields"],
                [
                    "used_akbp_context",
                    "akbp_context_item_ids",
                    "akbp_citation_ids",
                    "warnings_surfaced",
                    "fallback_reason",
                ],
            )
            self.assertIn("used_akbp_context to false", context_use["rules"][0])
            self.assertIn("trace back to result.context.items", context_use["rules"][1])
            self.assertIn("budget_truncated", context_use["fallback_reason_values"])
            self.assertFalse(prompt_contract["write_gate"]["required_for_apply"])
            provenance_gate = prompt_contract["source_provenance_gate"]
            self.assertEqual(provenance_gate["format"], "akbp-source-provenance-gate-v1")
            self.assertFalse(provenance_gate["required_before_preview"])
            self.assertIn("akbp.source.add", " ".join(provenance_gate["accepted_provenance"]))
            self.assertIn("model summary", " ".join(provenance_gate["reject_when"]))
            self.assertEqual(prompt_contract["write_gate"]["preview_flags"], {"dry_run": True})
            self.assertIn("error.code", prompt_contract["validation"]["branch_on"])
            self.assertIn("result.quality", prompt_contract["validation"]["preserve_fields"])
            self.assertIn("adapter_prompt_contract.context_use_report", prompt_contract["validation"]["preserve_fields"])
            self.assertEqual(
                read_only["quality_gates"]["startup_context"]["trust_gate_ref"],
                "adapter_prompt_contract.startup_trust_gate",
            )
            self.assertEqual(
                read_only["quality_gates"]["reviewed_writes"]["provenance_gate_ref"],
                "adapter_prompt_contract.source_provenance_gate",
            )
            self.assertEqual(read_only["safety"]["write_policy"], "no_writes")

            portable = json.loads(
                run_cli("--path", str(kb), "client-config", "--name", "portable-adapter", "--portable").stdout
            )
            self.assertEqual(portable["knowledge_base"]["path"], "<AKBP_KB_PATH>")
            self.assertIn(
                "akbp --path <AKBP_KB_PATH> doctor --profile read-only",
                portable["profile_selection"]["profiles"][1]["required_preflight"],
            )
            self.assertEqual(portable["knowledge_base"]["card"], "<AKBP_KB_PATH>/akbp.json")
            self.assertTrue(portable["knowledge_base"]["portable_template"])
            self.assertEqual(portable["first_run_sequence"]["steps"][0]["expect"]["knowledge_base.path"], "<AKBP_KB_PATH>")
            self.assertEqual(portable["tool_protocol_bridge"]["host_tool_manifest"]["knowledge_base_path"], "<AKBP_KB_PATH>")
            self.assertEqual(portable["tool_protocol_bridge"]["host_tool_manifest"]["preflight_requests"][0]["path"], "<AKBP_KB_PATH>")
            portable_replay = [
                json.loads(line)
                for line in portable["tool_protocol_bridge"]["preflight_replay"]["request_jsonl"].splitlines()
            ]
            self.assertEqual(portable_replay[0]["path"], "<AKBP_KB_PATH>")
            self.assertEqual(portable["startup"]["path"], "<AKBP_KB_PATH>")
            self.assertEqual(portable["health_check"]["path"], "<AKBP_KB_PATH>")
            self.assertEqual(portable["session_start"]["path"], "<AKBP_KB_PATH>")
            self.assertEqual(portable["adapter_prompt_contract"]["startup_request"]["path"], "<AKBP_KB_PATH>")
            self.assertEqual(portable["multi_client_scope"]["shared_kb_path"], "<AKBP_KB_PATH>")
            self.assertEqual(portable["tool_protocol_bridge_snippets"]["server_process"]["env"]["AKBP_KB_PATH"], "<AKBP_KB_PATH>")
            self.assertEqual(
                portable["tool_protocol_bridge_snippets"]["host_server_template"]["toolServers"]["akbp"]["args"][3],
                "<AKBP_KB_PATH>",
            )
            self.assertTrue(portable["multi_client_scope"]["safe_for_public_templates"])
            self.assertTrue(portable["distribution"]["safe_to_commit"])
            self.assertEqual(portable["distribution"]["replace_before_run"], ["<AKBP_KB_PATH>"])
            self.assertIn(
                "akbp --path <AKBP_KB_PATH> client-config --profile read-only",
                portable["host_autodetect"]["required_install_review"],
            )
            self.assertIn("placeholders", portable["host_autodetect"]["public_template_rule"])

            startup_context = json.loads(
                run_cli("--path", str(kb), "client-config", "--profile", "startup-context").stdout
            )
            self.assertEqual(startup_context["startup"]["params"]["requires_profiles"], ["startup_context"])
            self.assertEqual(startup_context["tool_schema_budget"]["selected_profile"], "startup_context")
            self.assertEqual(startup_context["tool_schema_budget"]["max_exposed_methods_for_profile"], 4)
            self.assertEqual(
                startup_context["tool_schema_budget"]["exposed_methods"],
                ["akbp.capabilities", "akbp.doctor", "akbp.session.start", "akbp.context"],
            )
            self.assertTrue(startup_context["tool_schema_budget"]["within_budget"])
            self.assertEqual(startup_context["tool_schema_budget"]["budget_check"], "pass")
            self.assertEqual(startup_context["tool_schema_budget"]["overflow_methods"], [])
            self.assertTrue(startup_context["tool_schema_budget"]["preflight_gate"]["required_before_host_tool_exposure"])
            self.assertNotIn("akbp.search", startup_context["tool_schema_budget"]["exposed_methods"])
            self.assertEqual(
                startup_context["tool_protocol_bridge"]["read_only_allowlist"],
                startup_context["tool_schema_budget"]["exposed_methods"],
            )
            self.assertEqual(
                startup_context["host_capability_descriptor"]["profile_contracts"]["startup_context"]["methods"],
                startup_context["tool_schema_budget"]["exposed_methods"],
            )
            self.assertNotIn("write_apply_requires_approval", startup_context["startup"]["params"]["requires"])
            self.assertEqual(startup_context["health_check"]["params"]["profile"], "startup_context")
            self.assertEqual(startup_context["tool_protocol_bridge"]["host_tool_manifest"]["preflight_requests"][1]["params"]["profile"], "startup_context")
            self.assertEqual(
                startup_context["tool_protocol_bridge"]["host_tool_manifest"]["preflight_requests"][1]["expect"]["result.requested_profile"],
                "startup_context",
            )
            self.assertTrue(startup_context["tool_protocol_bridge"]["host_tool_manifest"]["preflight_requests"][1]["expect"]["result.requested_profile_ready"])
            self.assertTrue(startup_context["verification"][1]["expect"]["result.adapter_readiness.startup_context_ready"])
            self.assertEqual(startup_context["session_start"]["method"], "akbp.session.start")
            self.assertTrue(startup_context["quality_gates"]["startup_context"]["required_before_planning"])
            self.assertTrue(startup_context["adapter_prompt_contract"]["planning_gate"]["required_before_planning"])
            self.assertEqual(startup_context["safety"]["profile"], "startup_context")
            self.assertEqual(startup_context["safety"]["write_policy"], "no_writes")

            reviewed_writes = json.loads(
                run_cli("--path", str(kb), "client-config", "--profile", "reviewed-writes").stdout
            )
            self.assertEqual(reviewed_writes["adapter_prompt_contract"]["profile"], "reviewed_write")
            self.assertTrue(
                reviewed_writes["adapter_prompt_contract"]["source_provenance_gate"]["required_before_preview"]
            )
            self.assertTrue(reviewed_writes["quality_gates"]["reviewed_writes"]["required_for_apply"])
            self.assertIn(
                "adapter_prompt_contract.source_provenance_gate",
                reviewed_writes["quality_gates"]["reviewed_writes"]["provenance_gate_ref"],
            )

    def test_discover_finds_nearest_kb_and_reports_trust_boundary(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "repo"
            nested = kb / "src" / "agent"
            run_cli("--path", str(kb), "init")
            nested.mkdir(parents=True)

            discovered = json.loads(run_cli("--path", str(nested), "discover").stdout)
            self.assertTrue(discovered["found"])
            self.assertEqual(discovered["path"], str(kb.resolve()))
            self.assertEqual(discovered["card_path"], str(kb.resolve() / "akbp.json"))
            self.assertEqual(discovered["card"]["default_scope"], "project")
            self.assertEqual(discovered["trust_boundary"]["read_path"], str(kb.resolve()))
            self.assertIn("dry-run previews", discovered["trust_boundary"]["write_rule"])
            self.assertIn("doctor --profile", discovered["trust_boundary"]["adapter_rule"])
            self.assertEqual(discovered["positioning"]["primary_role"], "portable_reviewable_knowledge_artifacts")
            self.assertTrue(discovered["positioning"]["not_a_hidden_memory_store"])
            self.assertEqual(discovered["positioning"]["adapter_default"], "read_only_until_doctor_and_capabilities_pass")
            compared_layers = {item["layer"] for item in discovered["positioning"]["use_with"]}
            self.assertIn("memory_server_or_runtime_cache", compared_layers)
            self.assertIn("tool_protocol_host", compared_layers)
            triage = discovered["adoption_triage"]
            self.assertEqual(triage["format"], "akbp-adoption-triage-v1")
            self.assertIn("silent capture", triage["research_signal"])
            self.assertEqual([question["id"] for question in triage["questions"]], [
                "need_durable_project_truth",
                "can_preserve_citations",
                "has_review_surface",
            ])
            self.assertIn("prove cited startup context", triage["recommended_path"])
            self.assertIn("adapter drops error.code or warnings", triage["fail_closed_when"])
            selection = discovered["profile_selection"]
            self.assertEqual(selection["format"], "akbp-adapter-profile-selection-v1")
            self.assertEqual(selection["safe_default"], "read_only")
            self.assertEqual([profile["profile"] for profile in selection["profiles"]], ["startup_context", "read_only", "reviewed_write"])
            self.assertIn("doctor --profile read-only", selection["profiles"][1]["required_preflight"][0])
            self.assertIn("approved:true", " ".join(selection["profiles"][2]["allowed_methods"]))
            self.assertIn("keep the integration read-only", selection["fallback"])
            schema_budget = discovered["tool_schema_budget"]
            self.assertEqual(schema_budget["format"], "akbp-tool-schema-budget-v1")
            self.assertEqual(schema_budget["selected_profile"], "read_only")
            self.assertEqual(schema_budget["exposed_method_count"], len(schema_budget["exposed_methods"]))
            self.assertTrue(schema_budget["within_budget"])
            self.assertEqual(schema_budget["budget_check"], "pass")
            self.assertEqual(schema_budget["max_exposed_methods_for_profile"], 8)
            self.assertIn("akbp.search", schema_budget["exposed_methods"])
            self.assertIn("akbp.import_apply", schema_budget["blocked_until_needed"])
            self.assertIn("exposed_method_count is greater than max_exposed_methods_for_profile", schema_budget["fail_closed_when"])
            self.assertIn("profile", " ".join(schema_budget["schema_strategy"]))
            self.assertIn("read-only allowlist", schema_budget["fallback"])
            autodetect = discovered["host_autodetect"]
            self.assertEqual(autodetect["format"], "akbp-host-autodetect-contract-v1")
            self.assertEqual(autodetect["safe_default"], "inventory_only")
            self.assertEqual(autodetect["selected_profile"], "read_only")
            self.assertIn("supports_stdio_tools", autodetect["inventory_fields"])
            self.assertIn("write host config files", autodetect["blocked_probe_actions"])
            self.assertIn("client-config --profile read-only", " ".join(autodetect["required_install_review"]))
            self.assertIn("do not mutate host config", autodetect["fallback"])
            memory_bridge = discovered["memory_server_bridge"]
            self.assertEqual(memory_bridge["format"], "akbp-memory-server-bridge-v1")
            self.assertEqual(memory_bridge["safe_default"], "treat_existing_memory_as_ephemeral_until_import_checked")
            self.assertIn("fast local recall", memory_bridge["use_existing_memory_for"])
            self.assertIn("akbp.import_check accepts the record without secret, schema, or evidence issues", memory_bridge["promote_to_akbp_when"])
            self.assertIn("memory rows have no source ids, citations, or review metadata", memory_bridge["fail_closed_when"])
            self.assertEqual(memory_bridge["promotion_contract_ref"], "external_memory_promotion")
            bridge_steps = {step["name"]: step for step in memory_bridge["minimum_preflight"]}
            self.assertIn("resolve_kb", bridge_steps)
            self.assertIn("stage_external_memory", bridge_steps)
            self.assertIn("import-check", bridge_steps["stage_external_memory"]["command"])
            bridge_preflight = discovered["tool_protocol_bridge_preflight"]
            self.assertEqual(bridge_preflight["format"], "akbp-discovery-tool-protocol-bridge-v1")
            self.assertEqual(bridge_preflight["safe_default"], "read_only_bridge")
            self.assertIn("client-config --profile read-only", bridge_preflight["next_command"])
            self.assertEqual(bridge_preflight["runnable_preflight"], "./examples/tool-protocol-bridge/run.sh")
            self.assertIn("akbp.session.start", bridge_preflight["read_only_methods"])
            self.assertIn("akbp.import_check", bridge_preflight["read_only_methods"])
            self.assertIn("akbp.remember", bridge_preflight["blocked_direct_methods"])
            self.assertIn("akbp.import_apply", bridge_preflight["blocked_direct_methods"])
            self.assertIn("error.code", " ".join(bridge_preflight["must_preserve"]))
            self.assertIn("dry-run preview", " ".join(bridge_preflight["enable_reviewed_writes_after"]))
            self.assertIn("read-only startup context", bridge_preflight["fallback"])
            external_promotion = discovered["external_memory_promotion"]
            self.assertEqual(external_promotion["format"], "akbp-external-memory-promotion-v1")
            self.assertEqual(external_promotion["safe_default"], "import_check_before_apply")
            self.assertEqual(
                external_promotion["promotion_triage"]["decisions"][2]["action"],
                "import_check_then_dry_run_preview",
            )
            intake = external_promotion["intake_classification"]
            self.assertEqual(intake["format"], "akbp-memory-intake-classification-v1")
            self.assertEqual(
                [item["class"] for item in intake["classes"]],
                [
                    "runtime_scratch",
                    "ephemeral_hint",
                    "candidate_durable_claim",
                    "blocked_private_or_secret",
                ],
            )
            self.assertIn("source value or AKBP source id", intake["minimum_fields_before_candidate"])
            self.assertIn("only candidate_durable_claim rows", intake["adapter_rule"])
            self.assertIn("source.value", external_promotion["required_review_fields"])
            self.assertIn("runtime_cache_metadata_only", external_promotion["reject_reasons"])
            promotion_steps = {step["step"]: step for step in external_promotion["promotion_sequence"]}
            self.assertIn("check_import", promotion_steps)
            self.assertIn("import-check", promotion_steps["check_import"]["command"])
            self.assertIn("ephemeral hint", external_promotion["fallback"])
            self.assertIn("reviewed portable artifact layer", memory_bridge["adapter_message"])
            inherited_intake = discovered["inherited_repo_intake"]
            self.assertEqual(inherited_intake["format"], "akbp-inherited-repo-intake-v1")
            self.assertIn("agent-written repository", inherited_intake["purpose"])
            risk_triage = inherited_intake["takeover_risk_triage"]
            self.assertEqual(risk_triage["format"], "akbp-inherited-repo-risk-triage-v1")
            self.assertEqual(
                [item["class"] for item in risk_triage["classes"]],
                [
                    "fresh_repo_no_prior_memory",
                    "source_verified_read_only",
                    "review_required",
                    "blocked_private_or_secret",
                ],
            )
            self.assertIn("source verify --fail-on-issue", " ".join(risk_triage["minimum_green_path"]))
            self.assertIn("no inherited AKBP memory", risk_triage["adapter_rule"])
            self.assertIn("source verify --fail-on-issue", json.dumps(inherited_intake["preflight_sequence"]))
            self.assertIn("uncited inherited notes", inherited_intake["trust_gate"]["fail_closed_on"])
            self.assertEqual(inherited_intake["example"], "./examples/inherited-repo-intake/run.sh")
            self.assertEqual(discovered["first_run_proof"]["safe_default"], "read_only")
            ten_minute = discovered["ten_minute_proof"]
            self.assertEqual(ten_minute["format"], "akbp-ten-minute-proof-v1")
            self.assertIn("local, cited, review-gated, and portable", ten_minute["purpose"])
            self.assertTrue(ten_minute["setup_claims"]["local_first"])
            self.assertFalse(ten_minute["setup_claims"]["requires_secrets"])
            proof_steps = {item["name"]: item for item in ten_minute["proof_steps"]}
            self.assertIn("create_visible_artifacts", proof_steps)
            self.assertIn("retrieve_cited_context", proof_steps)
            self.assertIn("block_unapproved_apply", proof_steps)
            self.assertIn("validate_adapter_response_contract", proof_steps)
            self.assertIn("export_portable_bundle", proof_steps)
            self.assertIn("--require-citations", proof_steps["retrieve_cited_context"]["command"])
            self.assertIn("structured-output-harness", proof_steps["validate_adapter_response_contract"]["command"])
            self.assertIn("approval_required", " ".join(ten_minute["success_markers"]))
            self.assertIn("structured-output harness", " ".join(ten_minute["success_markers"]))
            self.assertEqual(
                discovered["first_run_proof"]["recommended_harness"]["command"],
                "./examples/structured-output-harness/run.sh",
            )
            self.assertIn("approval_required", discovered["first_run_proof"]["recommended_harness"]["purpose"])
            self.assertIn("read-only", discovered["first_run_proof"]["recommended_harness"]["stop_policy"])
            prompt_contract = discovered["adapter_prompt_contract"]
            self.assertEqual(prompt_contract["format"], "akbp-adapter-prompt-contract-v1")
            self.assertEqual(prompt_contract["required_startup_call"]["method"], "akbp.session.start")
            self.assertEqual(prompt_contract["required_startup_call"]["path"], str(kb.resolve()))
            self.assertEqual(prompt_contract["required_startup_call"]["params"]["max_chars"], 4000)
            self.assertIn("dry_run:true", " ".join(prompt_contract["system_rules"]))
            self.assertIn("source ids", " ".join(prompt_contract["system_rules"]))
            self.assertIn("do not invent prior decisions", prompt_contract["planning_gate"]["fallback"])
            self.assertTrue(prompt_contract["planning_gate"]["required_before_planning"])
            context_use = prompt_contract["context_use_report"]
            self.assertEqual(context_use["format"], "akbp-context-use-report-v1")
            self.assertIn("used_akbp_context", context_use["required_fields"])
            self.assertIn("akbp_citation_ids", context_use["required_fields"])
            self.assertIn("budget_truncated", context_use["fallback_reason_values"])
            self.assertIn("trace back to result.context.items", " ".join(context_use["rules"]))
            trust_gate = prompt_contract["startup_trust_gate"]
            self.assertEqual(trust_gate["format"], "akbp-startup-trust-gate-v1")
            self.assertTrue(trust_gate["required_before_planning"])
            self.assertTrue(trust_gate["trust_conditions"]["require_citations"])
            self.assertIn("budget.truncated", " ".join(trust_gate["fail_closed_on"]))
            self.assertEqual(prompt_contract["write_gate"]["apply_flags"], {"approved": True})
            provenance_gate = prompt_contract["source_provenance_gate"]
            self.assertEqual(provenance_gate["format"], "akbp-source-provenance-gate-v1")
            self.assertTrue(provenance_gate["required_before_preview"])
            self.assertIn("source ids", " ".join(provenance_gate["accepted_provenance"]))
            self.assertIn("runtime scratch", provenance_gate["fallback"])
            self.assertIn(
                "adapter_prompt_contract.context_use_report",
                prompt_contract["validation"]["preserve_fields"],
            )
            self.assertIn(
                "adapter_prompt_contract.startup_trust_gate",
                prompt_contract["validation"]["preserve_fields"],
            )
            response_contract = discovered["response_contract"]
            self.assertEqual(response_contract["format"], "akbp-discovery-response-contract-v1")
            self.assertEqual(response_contract["envelope"]["required"], ["id", "ok", "result", "error"])
            self.assertTrue(response_contract["startup_context_gate"]["required_before_planning"])
            self.assertIn("missing citations", response_contract["startup_context_gate"]["fail_closed_on"])
            self.assertEqual(response_contract["write_gate"]["preview_required"], "dry_run:true")
            self.assertIn("preview_fingerprint", response_contract["write_gate"]["required_preview_fields"])
            self.assertIn("structured-output-harness", response_contract["harness"]["command"])
            proof_steps = {item["name"]: item for item in discovered["first_run_proof"]["steps"]}
            self.assertIn("doctor_read_only", proof_steps)
            self.assertIn("retrieve_startup_context", proof_steps)
            self.assertIn("preview_before_write", proof_steps)
            self.assertIn("block_unapproved_write", proof_steps)
            self.assertIn("validate_adapter_response_contract", proof_steps)
            self.assertIn("approval_required", proof_steps["block_unapproved_write"]["expect"])
            self.assertIn("structured-output-harness", proof_steps["validate_adapter_response_contract"]["command"])
            self.assertIn("dry-run preview", " ".join(discovered["first_run_proof"]["enable_reviewed_writes_when"]))
            self.assertIn("doctor --profile read-only", discovered["recommended_commands"]["doctor"])
            self.assertEqual(discovered["missing_artifacts"], [])

            missing = subprocess.run(
                [sys.executable, str(CLI), "--path", str(Path(d) / "outside"), "discover"],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(missing.returncode, 1)
            missing_payload = json.loads(missing.stdout)
            self.assertFalse(missing_payload["found"])
            self.assertIn("akbp.json", missing_payload["warnings"][0])

    def test_doctor_recommends_startup_context_for_initialized_kb_without_index(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            run_cli("--path", str(kb), "init")
            doctor = json.loads(run_cli("--path", str(kb), "doctor").stdout)
            self.assertEqual(doctor["adapter_readiness"]["recommended_profile"], "startup_context")
            self.assertEqual(doctor["security_posture"]["write_boundary"], "dry_run_preview_then_approved_apply")
            self.assertEqual(doctor["security_posture"]["approval_field"], "approved")
            self.assertTrue(doctor["security_posture"]["redaction"]["tool_server_error_output"])
            self.assertIn("akbp.import_check", doctor["security_posture"]["safe_review_methods"])
            self.assertTrue(doctor["adapter_readiness"]["startup_context_ready"])
            self.assertFalse(doctor["adapter_readiness"]["read_only_ready"])
            self.assertFalse(doctor["adapter_readiness"]["reviewed_write_ready"])
            self.assertEqual(doctor["adapter_readiness"]["startup_context_missing"], [])
            self.assertIn("index", doctor["adapter_readiness"]["read_only_missing"])

            read_only = subprocess.run(
                [sys.executable, str(CLI), "--path", str(kb), "doctor", "--profile", "read-only"],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(read_only.returncode, 1)
            read_only_doctor = json.loads(read_only.stdout)
            self.assertEqual(read_only_doctor["requested_profile"], "read_only")
            self.assertFalse(read_only_doctor["requested_profile_ready"])
            self.assertFalse(read_only_doctor["adapter_readiness"]["read_only_ready"])

            startup_context = json.loads(
                run_cli("--path", str(kb), "doctor", "--profile", "startup-context").stdout
            )
            self.assertEqual(startup_context["requested_profile"], "startup_context")
            self.assertTrue(startup_context["requested_profile_ready"])

    def test_source_verify_uses_cwd_fallback_for_relative_file_sources(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            run_cli("--path", str(kb), "init")
            cwd_file = Path.cwd() / "akbp-cwd-source-smoke.txt"
            try:
                cwd_file.write_text("cwd source", encoding="utf-8")
                source = json.loads(
                    run_cli("--path", str(kb), "source", "add", cwd_file.name, "--type", "file").stdout
                )
                verified = json.loads(
                    run_cli("--path", str(kb), "source", "verify", source["id"], "--fail-on-issue").stdout
                )
                self.assertTrue(verified["ok"])
                self.assertEqual(verified["counts"]["verified"], 1)
            finally:
                cwd_file.unlink(missing_ok=True)


    def test_quickstart_demo_script_passes(self):
        demo_dir = ROOT / "examples" / "quickstart-demo"
        with tempfile.TemporaryDirectory() as tmp:
            kb = Path(tmp) / "demo-kb"
            result = subprocess.run(
                [str(demo_dir / "run.sh"), str(kb)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=True,
            )
            self.assertIn("AKBP quickstart demo passed", result.stdout)
            self.assertTrue((kb / "export.json").is_file())
            self.assertTrue((kb / ".akbp" / "state.db").is_file())

    def test_init_remember_query_lint(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            out = run_cli("--path", str(kb), "init", "--level", "0")
            self.assertIn("Initialized AKBP Level 0 knowledge base", out.stdout)
            self.assertTrue((kb / "wiki" / "index.md").exists())
            self.assertTrue((kb / "AKBP.md").exists())
            conformance = json.loads(run_cli("--path", str(kb), "conformance", "--level", "0").stdout)
            self.assertTrue(conformance["levels"]["0"]["ok"])
            audit_log = (kb / ".akbp" / "audit.log.jsonl").read_text(encoding="utf-8")
            self.assertIn('"level": "0"', audit_log)
            entrypoint = (kb / "AKBP.md").read_text(encoding="utf-8")
            self.assertIn("## Memory rules", entrypoint)
            self.assertIn("Use `akbp.context` or `akbp.session.start` before planning", entrypoint)
            self.assertIn("Supersede or contradict stale claims instead of silently rewriting history", entrypoint)
            self.assertIn("durable writes require explicit approval", entrypoint)
            card = json.loads((kb / "akbp.json").read_text(encoding="utf-8"))
            self.assertEqual(card["schema_version"], "0.1-draft")
            self.assertIn("claims", card["artifacts"])
            (kb / "README.md").write_text("# Readme\n", encoding="utf-8")

            out = run_cli("--path", str(kb), "source", "add", "README.md", "--type", "file", "--title", "Readme")
            source = json.loads(out.stdout)
            self.assertTrue(source["id"].startswith("source_"))

            out = run_cli(
                "--path", str(kb),
                "remember",
                "This project uses Bun instead of npm",
                "--type", "decision",
                "--evidence", source["id"],
            )
            claim = json.loads(out.stdout)
            self.assertEqual(claim["type"], "decision")
            run_cli(
                "--path", str(kb),
                "remember",
                "Database migrations use small verified batches",
                "--type", "workflow",
                "--evidence", source["id"],
            )

            out = run_cli("--path", str(kb), "query", "Bun npm")
            results = json.loads(out.stdout)["results"]
            self.assertTrue(results)

            out = run_cli("--path", str(kb), "index")
            indexed = json.loads(out.stdout)
            self.assertGreaterEqual(indexed["rows"], 1)
            self.assertGreaterEqual(len(indexed["indexed_keys"]), 1)
            out = run_cli("--path", str(kb), "search", "Bun")
            searched = json.loads(out.stdout)
            self.assertEqual(searched["backend"], "sqlite_fts5")
            self.assertTrue(searched["results"])

            entity = {
                "id": "entity_agentmemory",
                "name": "AgentMemory",
                "type": "tool",
                "aliases": ["hybrid recall"],
                "description": "JSONL observation log for durable agent context",
                "created_at": "2026-05-01T00:00:00Z",
            }
            relation = {
                "id": "relation_agentmemory_references_recall",
                "source": "entity_agentmemory",
                "relation": "references",
                "target": "entity_hybrid_recall",
                "confidence": 0.8,
                "evidence": [source["id"]],
                "created_at": "2026-05-01T00:00:00Z",
            }
            (kb / "graph" / "entities.jsonl").write_text(json.dumps(entity) + "\n", encoding="utf-8")
            (kb / "graph" / "relations.jsonl").write_text(json.dumps(relation) + "\n", encoding="utf-8")
            run_cli("--path", str(kb), "index")

            out = run_cli("--path", str(kb), "search", "AgentMemory")
            searched = json.loads(out.stdout)
            self.assertTrue(any(item["type"] == "entity" and item["id"] == "entity_agentmemory" for item in searched["results"]))

            out = run_cli("--path", str(kb), "search", "Readme")
            searched = json.loads(out.stdout)
            self.assertTrue(any(item["type"] == "source" and item["id"] == source["id"] for item in searched["results"]))

            out = run_cli("--path", str(kb), "search", "references hybrid recall")
            searched = json.loads(out.stdout)
            self.assertTrue(any(item["type"] == "relation" and item["id"] == "relation_agentmemory_references_recall" for item in searched["results"]))

            out = run_cli("--path", str(kb), "search", "Bun: npm OR migration")
            searched = json.loads(out.stdout)
            self.assertEqual(searched["fts_query"], '"Bun" OR "npm" OR "migration"')
            self.assertTrue(searched["results"])

            out = run_cli("--path", str(kb), "search", "Bun AND npm")
            searched = json.loads(out.stdout)
            self.assertEqual(searched["fts_query"], '"Bun" AND "npm"')
            self.assertTrue(any("Bun" in item["snippet"] for item in searched["results"]))

            out = run_cli("--path", str(kb), "search", "Bun NOT migration")
            searched = json.loads(out.stdout)
            self.assertEqual(searched["fts_query"], '"Bun" NOT "migration"')
            self.assertTrue(searched["results"])

            out = run_cli("--path", str(kb), "search", '"small verified" batches')
            searched = json.loads(out.stdout)
            self.assertEqual(searched["fts_query"], '"small verified" OR "batches"')
            self.assertTrue(any("small verified" in item["snippet"] for item in searched["results"]))

            out = run_cli("--path", str(kb), "search", "database/migrations; small_verified!")
            searched = json.loads(out.stdout)
            self.assertEqual(searched["fts_query"], '"database/migrations" OR "small_verified"')
            self.assertTrue(searched["results"])

            out = run_cli("--path", str(kb), "search", "migra*")
            searched = json.loads(out.stdout)
            self.assertEqual(searched["fts_query"], "migra*")
            self.assertTrue(any("migration" in item["snippet"].lower() for item in searched["results"]))

            out = run_cli("--path", str(kb), "search", "Bun AND migra*")
            searched = json.loads(out.stdout)
            self.assertEqual(searched["fts_query"], '"Bun" AND migra*')
            self.assertTrue(searched["results"])

            out = run_cli("--path", str(kb), "search", "Bun - migration")
            searched = json.loads(out.stdout)
            self.assertEqual(searched["fts_query"], '"Bun" OR "migration"')
            self.assertTrue(searched["results"])

            out = run_cli("--path", str(kb), "search", "NOT migration")
            searched = json.loads(out.stdout)
            self.assertEqual(searched["backend"], "sqlite_fts5")
            self.assertEqual(searched["fts_query"], "")
            self.assertEqual(searched["results"], [])

            out = run_cli("--path", str(kb), "search", "!!!")
            searched = json.loads(out.stdout)
            self.assertEqual(searched["backend"], "sqlite_fts5")
            self.assertEqual(searched["fts_query"], "")
            self.assertEqual(searched["results"], [])

            out = run_cli("--path", str(kb), "search", "AND OR NOT")
            searched = json.loads(out.stdout)
            self.assertEqual(searched["backend"], "sqlite_fts5")
            self.assertEqual(searched["fts_query"], "")
            self.assertEqual(searched["results"], [])

            out = run_cli("--path", str(kb), "search", "Bun AND")
            searched = json.loads(out.stdout)
            self.assertEqual(searched["backend"], "sqlite_fts5")
            self.assertEqual(searched["fts_query"], '"Bun"')
            self.assertTrue(searched["results"])

            out = run_cli("--path", str(kb), "index", "--incremental")
            indexed_again = json.loads(out.stdout)
            self.assertGreaterEqual(indexed_again["skipped"], 1)
            self.assertTrue(indexed_again["incremental"])
            self.assertGreaterEqual(len(indexed_again["skipped_keys"]), 1)
            self.assertEqual(indexed_again["removed_keys"], [])

            out = run_cli("--path", str(kb), "context", "continue Bun npm migration")
            pack = json.loads(out.stdout)
            self.assertEqual(pack["query"], "continue Bun npm migration")
            self.assertTrue(pack["items"])
            self.assertEqual(pack["items"][0]["backend"], "sqlite_fts5")
            self.assertIn("citations", pack["items"][0])
            self.assertTrue(pack["quality"]["ok"])

            out = run_cli(
                "--path", str(kb),
                "context", "continue Bun npm migration",
                "--min-items", "1",
                "--require-citations",
            )
            gated_pack = json.loads(out.stdout)
            self.assertTrue(gated_pack["quality"]["ok"])
            self.assertEqual(gated_pack["quality"]["minimum_items"], 1)
            self.assertTrue(gated_pack["quality"]["require_citations"])

            empty_gate = subprocess.run(
                [
                    sys.executable,
                    str(CLI),
                    "--path", str(kb),
                    "context", "zzzz-unmatched-startup-context-gate",
                    "--min-items", "1",
                    "--require-citations",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(empty_gate.returncode, 1)
            empty_pack = json.loads(empty_gate.stdout)
            self.assertFalse(empty_pack["quality"]["ok"])
            self.assertIn("minimum_items:0<1", empty_pack["quality"]["failed"])
            self.assertTrue(any("Context quality gate failed" in warning for warning in empty_pack["warnings"]))

            out = run_cli("--path", str(kb), "context", "continue Bun npm migration", "--max-chars", "40")
            budgeted = json.loads(out.stdout)
            self.assertLessEqual(budgeted["budget"]["summary_chars"], 40)
            self.assertGreaterEqual(budgeted["budget"]["truncated_items"], 1)
            self.assertTrue(budgeted["budget"]["truncated"])
            self.assertTrue(any("Context budget truncated" in warning for warning in budgeted["warnings"]))

            out = run_cli("--path", str(kb), "export")
            exported = json.loads(out.stdout)
            self.assertTrue(exported["claims"])
            self.assertTrue(exported["sources"])
            self.assertEqual(exported["manifest"]["format"], "akbp-portable-bundle")
            self.assertEqual(exported["manifest"]["counts"]["claims"], len(exported["claims"]))
            self.assertEqual(exported["manifest"]["counts"]["sources"], len(exported["sources"]))
            self.assertTrue(exported["manifest"]["safety"]["excludes_indexes"])
            self.assertEqual(exported["manifest"]["verification"]["hash_algorithm"], "sha256")

            out = run_cli("--path", str(kb), "source", "verify", "--fail-on-issue")
            source_verify = json.loads(out.stdout)
            self.assertTrue(source_verify["ok"])
            self.assertEqual(source_verify["counts"]["verified"], 1)
            missing_source_verify = subprocess.run(
                [
                    sys.executable,
                    str(CLI),
                    "--path",
                    str(kb),
                    "source",
                    "verify",
                    "source_missing",
                    "--fail-on-issue",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(missing_source_verify.returncode, 1)
            missing_source = json.loads(missing_source_verify.stdout)
            self.assertFalse(missing_source["ok"])
            self.assertEqual(missing_source["counts"]["checked"], 0)
            self.assertEqual(missing_source["counts"]["missing"], 1)
            self.assertEqual(missing_source["missing"][0]["reason"], "source_not_found")
            self.assertEqual(missing_source["attention"]["recommended_action"], "review_sources")
            self.assertEqual(missing_source["attention"]["missing_source_ids"], ["source_missing"])
            out = run_cli("--path", str(kb), "doctor")
            doctor = json.loads(out.stdout)
            self.assertTrue(doctor["ok"])
            self.assertTrue(doctor["ready_for_adapter"])
            self.assertEqual(doctor["adapter_readiness"]["recommended_profile"], "reviewed_write")
            self.assertTrue(doctor["adapter_readiness"]["startup_context_ready"])
            self.assertTrue(doctor["adapter_readiness"]["read_only_ready"])
            self.assertTrue(doctor["adapter_readiness"]["reviewed_write_ready"])
            self.assertEqual(doctor["adapter_readiness"]["blocking_checks"], [])
            self.assertEqual(doctor["summary"]["errors"], 0)
            self.assertEqual(doctor["next_steps"], [])
            (kb / "README.md").write_text("changed", encoding="utf-8")
            changed_verify = json.loads(run_cli("--path", str(kb), "source", "verify").stdout)
            self.assertFalse(changed_verify["ok"])
            self.assertEqual(changed_verify["counts"]["changed"], 1)
            affected = changed_verify["changed"][0]["affected_claims"]
            self.assertIn(claim["id"], affected)
            self.assertTrue(changed_verify["attention"]["requires_review"])
            self.assertEqual(changed_verify["attention"]["recommended_action"], "review_affected_claims")
            self.assertEqual(changed_verify["attention"]["changed_source_ids"], [source["id"]])
            self.assertEqual(changed_verify["attention"]["missing_source_ids"], [])
            self.assertIn(claim["id"], changed_verify["attention"]["affected_claims"])

            bundle = Path(d) / "bundle.json"
            bundle.write_text(json.dumps(exported), encoding="utf-8")
            checked = json.loads(run_cli("--path", str(kb), "export-check", str(bundle), "--fail-on-issues").stdout)
            self.assertTrue(checked["ok"])
            self.assertEqual(checked["manifest_format"], "akbp-portable-bundle")
            self.assertEqual(checked["counts"]["claims"], len(exported["claims"]))

            bad_bundle = Path(d) / "bad-bundle.json"
            bad = dict(exported)
            bad["manifest"] = dict(exported["manifest"])
            bad["manifest"]["counts"] = dict(exported["manifest"]["counts"])
            bad["manifest"]["counts"]["claims"] = 999
            bad_bundle.write_text(json.dumps(bad), encoding="utf-8")
            bad_check = json.loads(run_cli("--path", str(kb), "export-check", str(bad_bundle)).stdout)
            self.assertFalse(bad_check["ok"])
            self.assertTrue(any(issue["code"] == "count_mismatch" for issue in bad_check["issues"]))

            out = run_cli("--path", str(kb), "audit", "--limit", "10")
            audit = json.loads(out.stdout)
            self.assertGreaterEqual(audit["count"], 1)
            remember_events = [event for event in audit["events"] if event["event"] == "remember"]
            self.assertTrue(remember_events)
            self.assertEqual(remember_events[-1]["operation"]["actor"], "akbp-cli")
            self.assertEqual(remember_events[-1]["operation"]["mode"], "write")
            self.assertEqual(remember_events[-1]["operation"]["outcome"], "ok")

            out = run_cli("--path", str(kb), "status")
            status = json.loads(out.stdout)
            self.assertEqual(status["sources"], 1)
            self.assertTrue(status["card"])
            self.assertTrue(status["entrypoint"])
            self.assertGreaterEqual(status["counts"]["claims"], 2)
            self.assertGreaterEqual(status["counts"]["audit_events"], 1)
            self.assertTrue(status["claim_summary"]["latest"])

            self.assertIn("working", status["claim_summary"]["by_status"])
            self.assertFalse(status["source_health"]["ok"])
            self.assertEqual(status["source_health"]["counts"]["changed"], 1)
            self.assertIn(claim["id"], status["source_health"]["attention"]["changed"][0]["affected_claims"])
            self.assertTrue(status["index"]["present"])
            self.assertEqual(status["conformance"]["highest_passing_level"], "3")
            self.assertEqual(status["adapter_readiness"]["recommended_profile"], "setup_only")
            self.assertFalse(status["adapter_readiness"]["read_only_ready"])
            self.assertFalse(status["adapter_readiness"]["reviewed_write_ready"])
            self.assertIn("source_health", status["adapter_readiness"]["blocking_checks"])

            out = run_cli("--path", str(kb), "context", "Bun runtime decision")
            drift_pack = json.loads(out.stdout)
            self.assertTrue(any(source["id"] in warning and "changed" in warning for warning in drift_pack["warnings"]))

            out = run_cli("--path", str(kb), "search", "Bun runtime decision")
            drift_search = json.loads(out.stdout)
            self.assertTrue(any(source["id"] in warning and "changed" in warning for warning in drift_search["warnings"]))

            out = run_cli("--path", str(kb), "cite", claim["id"])
            citation = json.loads(out.stdout)
            self.assertEqual(citation["claim_id"], claim["id"])
            self.assertEqual(citation["evidence"], [source["id"]])

            out = run_cli(
                "--path", str(kb),
                "supersede", claim["id"],
                "This project uses Python stdlib for the reference CLI",
                "--type", "decision",
                "--evidence", "cli/akbp.py",
            )
            new_claim = json.loads(out.stdout)
            self.assertEqual(new_claim["supersedes"], [claim["id"]])
            out = run_cli("--path", str(kb), "search", "stdlib")
            search = json.loads(out.stdout)
            self.assertTrue(search["results"])
            self.assertIn("warnings", search)
            out = run_cli("--path", str(kb), "context", "Bun Python stdlib")
            pack = json.loads(out.stdout)
            context_claim_ids = [item["id"] for item in pack["items"] if item["type"] == "claim"]
            self.assertIn(new_claim["id"], context_claim_ids)
            self.assertNotIn(claim["id"], context_claim_ids)
            self.assertTrue(any(claim["id"] in warning for warning in pack["warnings"]))
            out = run_cli("--path", str(kb), "search", "Bun Python stdlib")
            search = json.loads(out.stdout)
            self.assertTrue(any(claim["id"] in warning for warning in search["warnings"]))

            out = run_cli(
                "--path", str(kb),
                "remember",
                "This project should use a packaged binary immediately",
                "--type", "decision",
                "--evidence", source["id"],
            )
            conflicting_claim = json.loads(out.stdout)
            out = run_cli("--path", str(kb), "contradict", new_claim["id"], conflicting_claim["id"], "--evidence", source["id"] )
            relation = json.loads(out.stdout)
            self.assertEqual(relation["relation"], "contradicts")

            out = run_cli("--path", str(kb), "conformance", "--level", "3")
            conformance = json.loads(out.stdout)
            self.assertTrue(conformance["ok"])
            self.assertTrue(conformance["levels"]["0"]["ok"])
            self.assertTrue(conformance["levels"]["1"]["ok"])
            self.assertTrue(conformance["levels"]["2"]["ok"])
            self.assertTrue(conformance["levels"]["3"]["ok"])

            out = run_cli("--path", str(kb), "lint")
            self.assertTrue(json.loads(out.stdout)["ok"])

    def test_doctor_reports_actionable_first_run_gaps(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            out = subprocess.run(
                [sys.executable, str(CLI), "--path", str(kb), "doctor"],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(out.returncode, 1)
            doctor = json.loads(out.stdout)
            self.assertFalse(doctor["ok"])
            self.assertFalse(doctor["ready_for_adapter"])
            self.assertEqual(doctor["adapter_readiness"]["recommended_profile"], "setup_only")
            self.assertFalse(doctor["adapter_readiness"]["startup_context_ready"])
            self.assertFalse(doctor["adapter_readiness"]["read_only_ready"])
            self.assertFalse(doctor["adapter_readiness"]["reviewed_write_ready"])
            self.assertIn("entrypoint", doctor["adapter_readiness"]["blocking_checks"])
            self.assertGreaterEqual(doctor["summary"]["errors"], 1)
            self.assertEqual(doctor["workflow"]["current_stage"], "create_kb")
            self.assertEqual(doctor["workflow"]["stages"][0]["id"], "create_kb")
            self.assertIn("Run: akbp --path <kb> init", doctor["next_steps"])

    def test_context_can_fail_on_warnings(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            note = Path(d) / "note.md"
            note.write_text("Decision: adapter startup gates should surface warning-bearing context before planning.\n", encoding="utf-8")
            run_cli("--path", str(kb), "init")
            run_cli(
                "--path", str(kb),
                "remember",
                "Adapter startup gates should surface warning-bearing context before planning from recalled memory.",
                "--type", "workflow",
                "--evidence", str(note),
            )

            out = run_cli(
                "--path", str(kb),
                "context",
                "adapter startup warning context",
                "--max-chars", "24",
                "--min-items", "1",
                "--require-citations",
            )
            pack = json.loads(out.stdout)
            self.assertTrue(pack["quality"]["ok"])
            self.assertTrue(pack["warnings"])

            proc = subprocess.run(
                [
                    sys.executable,
                    str(CLI),
                    "--path",
                    str(kb),
                    "context",
                    "adapter startup warning context",
                    "--max-chars",
                    "24",
                    "--min-items",
                    "1",
                    "--require-citations",
                    "--fail-on-warnings",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 1)
            failed = json.loads(proc.stdout)
            self.assertFalse(failed["quality"]["ok"])
            self.assertTrue(failed["quality"]["fail_on_warnings"])
            self.assertIn("warnings:1", failed["quality"]["failed"])
            self.assertTrue(any("Context budget truncated" in warning for warning in failed["warnings"]))

    def test_ingest_imports_redacted_page_and_optional_claim(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            note = Path(d) / "note.md"
            note.write_text("# Release Note\n\nDecision: ship small batches.\napi_key=sk-example123456789\n", encoding="utf-8")

            run_cli("--path", str(kb), "init")
            out = run_cli(
                "--path", str(kb),
                "ingest", str(note),
                "--title", "Release note",
                "--claim", "The release process uses small batches.",
                "--claim-type", "decision",
            )
            data = json.loads(out.stdout)
            self.assertTrue(data["ok"])
            self.assertTrue(data["redacted"])
            page = kb / data["page"]
            self.assertTrue(page.exists())
            self.assertIn("[REDACTED]", page.read_text(encoding="utf-8"))
            self.assertNotIn("sk-example123456789", page.read_text(encoding="utf-8"))
            claims = [json.loads(line) for line in (kb / "claims" / "claims.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual(claims[0]["evidence"], [data["source_id"]])

    def test_source_add_redacts_secret_like_title(self):
        with tempfile.TemporaryDirectory() as tmp:
            kb = Path(tmp) / "kb"
            note = Path(tmp) / "note.md"
            note.write_text("# Note\n", encoding="utf-8")
            run_cli("--path", str(kb), "init")
            proc = run_cli(
                "--path",
                str(kb),
                "source",
                "add",
                str(note),
                "--type",
                "file",
                "--title",
                "Incident api_key=sk-live-demo",
            )
            data = json.loads(proc.stdout)
            self.assertEqual(data["title"], "Incident [REDACTED]")
            self.assertNotIn("sk-live-demo", (kb / "raw" / "sources" / "sources.jsonl").read_text(encoding="utf-8"))

    def test_ingest_redacts_secret_like_title(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            note = Path(d) / "note.md"
            note.write_text("# Safe note\n\nDecision: keep titles clean.\n", encoding="utf-8")
            run_cli("--path", str(kb), "init")
            title = "Incident token=sk-example-title-secret"
            result = run_cli("--path", str(kb), "ingest", str(note), "--title", title)
            payload = json.loads(result.stdout)
            self.assertTrue(payload["ok"])
            sources = (kb / "raw" / "sources" / "sources.jsonl").read_text(encoding="utf-8")
            page = (kb / payload["page"]).read_text(encoding="utf-8")
            self.assertNotIn("sk-example-title-secret", sources)
            self.assertNotIn("sk-example-title-secret", page)
            self.assertIn("[REDACTED]", sources)
            self.assertIn("[REDACTED]", page)

    def test_ingest_redacts_optional_claim_text(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            note = Path(d) / "note.md"
            note.write_text("# Incident Note\n\nBlocker: deployment failed.\n", encoding="utf-8")

            run_cli("--path", str(kb), "init")
            out = run_cli(
                "--path", str(kb),
                "ingest", str(note),
                "--claim", "Deployment failed because token=sk-example123456789 was copied into logs.",
                "--claim-type", "warning",
            )
            data = json.loads(out.stdout)
            self.assertTrue(data["ok"])
            self.assertTrue(data["redacted"])
            claims = [json.loads(line) for line in (kb / "claims" / "claims.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertIn("[REDACTED]", claims[0]["text"])
            self.assertNotIn("sk-example123456789", claims[0]["text"])
            self.assertNotIn("token=", claims[0]["text"])


    def test_import_check_rejects_secret_like_jsonl_objects(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            export = Path(d) / "session-export.jsonl"
            rows = [
                {"kind": "claim", "id": "claim_safe", "text": "Deployment failed after a redacted example token appeared."},
                {"kind": "claim", "id": "claim_unsafe", "text": "Deployment failed after token=sk-example123456789 appeared."},
            ]
            export.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

            out = run_cli("--path", str(kb), "import-check", str(export))
            data = json.loads(out.stdout)
            self.assertTrue(data["ok"])
            self.assertEqual(data["checked"], 2)
            self.assertEqual(data["accepted_count"], 1)
            self.assertEqual(data["rejected_count"], 1)
            self.assertEqual(data["error_count"], 0)
            self.assertFalse(data["fail_on_rejected"])
            self.assertEqual([item["id"] for item in data["accepted"]], ["claim_safe"])
            self.assertEqual([item["id"] for item in data["rejected"]], ["claim_unsafe"])
            self.assertNotIn("sk-example123456789", out.stdout)

            strict = subprocess.run([sys.executable, str(CLI), "--path", str(kb), "import-check", str(export), "--fail-on-rejected"], text=True, capture_output=True)
            self.assertEqual(strict.returncode, 1)
            strict_data = json.loads(strict.stdout)
            self.assertFalse(strict_data["ok"])
            self.assertTrue(strict_data["fail_on_rejected"])
            self.assertEqual(strict_data["rejected_count"], 1)
            self.assertNotIn("sk-example123456789", strict.stdout)


    def test_import_rejects_unknown_source_evidence_ids(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            export = Path(d) / "dangling-evidence.jsonl"
            export.write_text(json.dumps({
                "kind": "claim",
                "id": "claim_dangling_evidence",
                "text": "Claims imported from JSONL should cite known source records.",
                "type": "workflow",
                "status": "working",
                "confidence": 0.7,
                "evidence": ["source_missing"],
                "scope": "project",
            }) + "\n", encoding="utf-8")
            run_cli("--path", str(kb), "init")

            checked = json.loads(run_cli("--path", str(kb), "import-check", str(export)).stdout)
            self.assertTrue(checked["ok"])
            self.assertEqual(checked["accepted_count"], 0)
            self.assertEqual(checked["rejected_count"], 1)
            self.assertIn("unknown evidence source id", checked["rejected"][0]["reason"])

            proc = subprocess.run([sys.executable, str(CLI), "--path", str(kb), "import-apply", str(export), "--dry-run"], text=True, capture_output=True)
            self.assertEqual(proc.returncode, 1)
            applied = json.loads(proc.stdout)
            self.assertFalse(applied["ok"])
            self.assertEqual(applied["accepted_count"], 0)
            self.assertEqual(applied["rejected_count"], 1)
            self.assertIn("unknown evidence source id", applied["rejected"][0]["reason"])

    def test_import_rejects_non_list_claim_collections(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            export = Path(d) / "bad-claim-lists.jsonl"
            rows = [
                {
                    "kind": "claim",
                    "id": "claim_string_evidence",
                    "text": "Imported claims must keep evidence as a list.",
                    "type": "workflow",
                    "status": "working",
                    "confidence": 0.7,
                    "evidence": "source_not_a_list",
                    "scope": "project",
                },
                {
                    "kind": "claim",
                    "id": "claim_string_entities",
                    "text": "Imported claims must keep entities as a list.",
                    "type": "workflow",
                    "status": "working",
                    "confidence": 0.7,
                    "evidence": [],
                    "entities": "agent",
                    "scope": "project",
                },
            ]
            export.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            run_cli("--path", str(kb), "init")

            proc = subprocess.run([sys.executable, str(CLI), "--path", str(kb), "import-check", str(export), "--fail-on-rejected"], text=True, capture_output=True)
            self.assertEqual(proc.returncode, 1)
            checked = json.loads(proc.stdout)
            self.assertFalse(checked["ok"])
            self.assertEqual(checked["accepted_count"], 0)
            self.assertEqual(checked["rejected_count"], 2)
            reasons = [item["reason"] for item in checked["rejected"]]
            self.assertTrue(any("evidence must be a list" in reason for reason in reasons))
            self.assertTrue(any("entities must be a list of strings" in reason for reason in reasons))

    def test_import_apply_missing_file_returns_result_shape(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            missing = Path(d) / "missing-export.jsonl"
            run_cli("--path", str(kb), "init")
            proc = subprocess.run([sys.executable, str(CLI), "--path", str(kb), "import-apply", str(missing), "--dry-run"], text=True, capture_output=True)
            self.assertEqual(proc.returncode, 1)
            self.assertEqual(proc.stderr, "")
            data = json.loads(proc.stdout)
            self.assertFalse(data["ok"])
            self.assertEqual(data["file"], str(missing.resolve()))
            self.assertTrue(data["dry_run"])
            self.assertFalse(data["applied"])
            self.assertEqual(data["checked"], 0)
            self.assertEqual(data["error_count"], 1)
            self.assertEqual(data["would_write"], {"sources": [], "claims": []})
            self.assertEqual(data["skipped_existing"], {"sources": [], "claims": []})
            self.assertIn("file not found", data["errors"][0]["error"])

    def test_import_apply_failure_shape_includes_review_fields(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            export = Path(d) / "unsafe-export.jsonl"
            export.write_text(
                json.dumps({"kind": "claim", "id": "claim_unsafe", "text": "token=sk-example123456789", "type": "workflow", "status": "working", "confidence": 0.7, "evidence": []}) + "\n",
                encoding="utf-8",
            )
            run_cli("--path", str(kb), "init")
            proc = subprocess.run([sys.executable, str(CLI), "--path", str(kb), "import-apply", str(export), "--dry-run"], text=True, capture_output=True)
            self.assertEqual(proc.returncode, 1)
            data = json.loads(proc.stdout)
            self.assertFalse(data["ok"])
            self.assertFalse(data["applied"])
            self.assertEqual(data["would_write"], {"sources": [], "claims": []})
            self.assertEqual(data["skipped_existing"], {"sources": [], "claims": []})
            self.assertEqual(data["rejected_count"], 1)
            self.assertNotIn("sk-example123456789", proc.stdout)

    def test_import_check_accepts_export_shaped_source_and_claim_objects(self):
        with tempfile.TemporaryDirectory() as tmp:
            kb = Path(tmp) / "kb"
            source = {
                "id": "source_export_shaped",
                "type": "file",
                "locator": "notes.md",
                "title": "Export shaped source",
                "hash": None,
                "immutable": True,
                "scope": "project",
                "created_at": "2026-05-08T00:00:00Z",
                "metadata": {},
            }
            claim = {
                "id": "claim_export_shaped",
                "text": "Export-shaped claim objects can be imported without adding a kind field.",
                "type": "workflow",
                "status": "working",
                "confidence": 0.8,
                "evidence": ["source_export_shaped"],
                "entities": [],
                "supersedes": [],
                "superseded_by": None,
                "scope": "project",
                "created_at": "2026-05-08T00:00:00Z",
                "updated_at": "2026-05-08T00:00:00Z",
                "last_confirmed_at": None,
            }
            exchange = Path(tmp) / "exchange.jsonl"
            exchange.write_text(json.dumps(source) + "\n" + json.dumps(claim) + "\n", encoding="utf-8")
            run_cli("--path", str(kb), "init")
            checked = json.loads(run_cli("--path", str(kb), "import-check", str(exchange), "--fail-on-rejected").stdout)
            self.assertTrue(checked["ok"])
            self.assertEqual(checked["accepted_count"], 2)
            self.assertEqual(checked["rejected"], [])
            self.assertEqual([item["kind"] for item in checked["accepted"]], ["source", "claim"])

    def test_import_apply_requires_review_and_writes_accepted_objects(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            export = Path(d) / "safe-export.jsonl"
            rows = [
                {"kind": "source", "id": "source_imported_safe", "type": "transcript", "locator": "imports/safe.md", "title": "Safe import"},
                {"kind": "claim", "id": "claim_imported_safe", "text": "Imported JSONL apply writes accepted claims only.", "type": "workflow", "status": "working", "confidence": 0.7, "evidence": ["source_imported_safe"], "scope": "project"},
            ]
            export.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            run_cli("--path", str(kb), "init")

            dry = json.loads(run_cli("--path", str(kb), "import-apply", str(export), "--dry-run").stdout)
            self.assertTrue(dry["ok"])
            self.assertFalse(dry["applied"])
            self.assertEqual(dry["would_write"]["sources"], ["source_imported_safe"])
            self.assertEqual(dry["would_write"]["claims"], ["claim_imported_safe"])
            self.assertTrue(dry["review_required"])
            self.assertIn("--approved", dry["apply_instruction"])
            self.assertFalse((kb / "claims" / "claims.jsonl").read_text(encoding="utf-8").strip())

            blocked = subprocess.run([sys.executable, str(CLI), "--path", str(kb), "import-apply", str(export)], text=True, capture_output=True)
            self.assertEqual(blocked.returncode, 1)
            blocked_data = json.loads(blocked.stdout)
            self.assertTrue(blocked_data["review_required"])

            applied = json.loads(run_cli("--path", str(kb), "import-apply", str(export), "--approved").stdout)
            self.assertTrue(applied["ok"])
            self.assertTrue(applied["applied"])
            claims = [json.loads(line) for line in (kb / "claims" / "claims.jsonl").read_text(encoding="utf-8").splitlines()]
            sources = [json.loads(line) for line in (kb / "raw" / "sources" / "sources.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertIn("claim_imported_safe", {claim["id"] for claim in claims})
            self.assertIn("source_imported_safe", {source["id"] for source in sources})

            duplicate_dry = json.loads(run_cli("--path", str(kb), "import-apply", str(export), "--dry-run").stdout)
            self.assertEqual(duplicate_dry["would_write"], {"sources": [], "claims": []})
            self.assertEqual(duplicate_dry["skipped_existing"]["sources"], ["source_imported_safe"])
            self.assertEqual(duplicate_dry["skipped_existing"]["claims"], ["claim_imported_safe"])

            duplicate_apply = json.loads(run_cli("--path", str(kb), "import-apply", str(export), "--approved").stdout)
            self.assertTrue(duplicate_apply["ok"])
            self.assertEqual(duplicate_apply["would_write"], {"sources": [], "claims": []})
            claims_after_duplicate = [json.loads(line) for line in (kb / "claims" / "claims.jsonl").read_text(encoding="utf-8").splitlines()]
            sources_after_duplicate = [json.loads(line) for line in (kb / "raw" / "sources" / "sources.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual([claim["id"] for claim in claims_after_duplicate].count("claim_imported_safe"), 1)
            self.assertEqual([source["id"] for source in sources_after_duplicate].count("source_imported_safe"), 1)

    def test_import_check_and_apply_accept_portable_bundle_json(self):
        with tempfile.TemporaryDirectory() as d:
            producer = Path(d) / "producer"
            consumer = Path(d) / "consumer"
            note = producer / "handoff.md"
            bundle = Path(d) / "bundle.json"

            run_cli("--path", str(producer), "init")
            note.write_text("Decision: portable bundles should import directly after review.\n", encoding="utf-8")
            source = json.loads(run_cli("--path", str(producer), "source", "add", str(note), "--type", "file").stdout)
            run_cli(
                "--path", str(producer),
                "remember",
                "Portable bundles should import directly after review.",
                "--type", "decision",
                "--evidence", source["id"],
            )
            run_cli("--path", str(producer), "export", "--output", str(bundle))

            run_cli("--path", str(consumer), "init")
            checked = json.loads(run_cli("--path", str(consumer), "import-check", str(bundle), "--fail-on-rejected").stdout)
            self.assertTrue(checked["ok"])
            self.assertEqual(checked["accepted_count"], 2)
            self.assertEqual(checked["rejected_count"], 0)

            preview = json.loads(run_cli("--path", str(consumer), "import-apply", str(bundle), "--dry-run").stdout)
            self.assertTrue(preview["ok"])
            self.assertEqual(preview["would_write"]["sources"], [source["id"]])
            self.assertEqual(len(preview["would_write"]["claims"]), 1)

            applied = json.loads(run_cli("--path", str(consumer), "import-apply", str(bundle), "--approved").stdout)
            self.assertTrue(applied["applied"])
            run_cli("--path", str(consumer), "index", "--incremental")
            context = json.loads(run_cli("--path", str(consumer), "context", "portable bundles direct import").stdout)
            self.assertIn("Portable bundles should import directly", json.dumps(context))

    def test_ingest_dry_run_previews_redacted_writes_without_creating_kb(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            note = Path(d) / "note.md"
            note.write_text("# Import Preview\n\nDecision: preview before write.\napi_key=sk-example123456789\n", encoding="utf-8")

            out = run_cli(
                "--path", str(kb),
                "ingest", str(note),
                "--claim", "Preview import with token=sk-example123456789 before write.",
                "--dry-run",
            )
            data = json.loads(out.stdout)
            self.assertTrue(data["ok"])
            self.assertTrue(data["dry_run"])
            self.assertTrue(data["redacted"])
            self.assertIn("claims/claims.jsonl", data["would_write"])
            self.assertIn(".akbp/audit.log.jsonl", data["would_write"])
            self.assertNotIn("logs/audit.jsonl", data["would_write"])
            self.assertFalse((kb / "raw" / "sources" / "sources.jsonl").exists())
            self.assertFalse((kb / "claims" / "claims.jsonl").exists())
            self.assertFalse((kb / data["page"]).exists())


    def test_tool_server_approval_flow_example_behavior(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            run_cli("--path", str(kb), "init")
            text = "Agents need rollback paths before production changes"
            requests = "\n".join([
                json.dumps({
                    "id": "remember-preview",
                    "method": "akbp.remember",
                    "path": str(kb),
                    "dry_run": True,
                    "params": {"text": text, "type": "workflow", "evidence": ["release-review.md"]},
                }),
                json.dumps({
                    "id": "remember-unapproved",
                    "method": "akbp.remember",
                    "path": str(kb),
                    "params": {"text": text, "type": "workflow", "evidence": ["release-review.md"]},
                }),
                json.dumps({
                    "id": "remember-approved",
                    "method": "akbp.remember",
                    "path": str(kb),
                    "approved": True,
                    "params": {"text": text, "type": "workflow", "evidence": ["release-review.md"]},
                }),
                json.dumps({
                    "id": "index-approved",
                    "method": "akbp.index",
                    "path": str(kb),
                    "approved": True,
                    "params": {"incremental": True},
                }),
                json.dumps({
                    "id": "context",
                    "method": "akbp.context",
                    "path": str(kb),
                    "params": {"task": "prepare production release", "limit": 5},
                }),
            ]) + "\n"
            proc = subprocess.run([sys.executable, str(SERVER)], input=requests, text=True, capture_output=True, check=True, cwd=str(ROOT))
            lines = [json.loads(line) for line in proc.stdout.splitlines()]
            self.assertTrue(lines[0]["ok"])
            self.assertTrue(lines[0]["result"]["dry_run"])
            self.assertTrue(lines[0]["result"]["review_required"])
            self.assertIn("apply_instruction", lines[0]["result"])
            self.assertFalse(lines[1]["ok"])
            self.assertEqual(lines[1]["error"]["code"], "approval_required")
            self.assertTrue(lines[1]["error"]["details"]["review_required"])
            self.assertTrue(lines[2]["ok"])
            self.assertEqual(lines[2]["result"]["type"], "workflow")
            self.assertTrue(lines[3]["ok"])
            self.assertTrue(lines[3]["result"]["incremental"])
            self.assertTrue(lines[4]["ok"])
            self.assertTrue(lines[4]["result"]["items"])
            claims = (kb / "claims" / "claims.jsonl").read_text(encoding="utf-8")
            self.assertEqual(claims.count(text), 1)

    def test_crystallize_apply_creates_session_page_and_claim(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            transcript = Path(d) / "transcript.md"
            transcript.write_text("We decided to use SQLite for local state.\nTODO: add tool-server implementation.\n", encoding="utf-8")

            run_cli("--path", str(kb), "init")
            preview = json.loads(run_cli("--path", str(kb), "crystallize", str(transcript), "--dry-run").stdout)
            self.assertTrue(preview["dry_run"])
            self.assertFalse(preview["apply"])
            self.assertFalse(Path(preview["page"]).exists())

            out = run_cli("--path", str(kb), "crystallize", str(transcript), "--apply")
            data = json.loads(out.stdout)
            self.assertFalse(data["dry_run"])
            self.assertTrue(Path(data["page"]).exists())

            claims = [json.loads(line) for line in (kb / "claims" / "claims.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertTrue(any("SQLite" in claim["text"] for claim in claims))
            self.assertTrue(any(claim["type"] == "decision" for claim in claims))
            self.assertTrue(any(claim["type"] == "observation" for claim in claims))
            self.assertTrue(all(claim["evidence"][0].startswith("source_") for claim in claims))

            sources = [json.loads(line) for line in (kb / "raw" / "sources" / "sources.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual(sources[0]["type"], "transcript")

            out = run_cli("--path", str(kb), "crystallize", str(transcript), "--apply")
            rerun = json.loads(out.stdout)
            self.assertTrue(rerun["skipped_claims"])

            conflict = subprocess.run(
                [sys.executable, str(CLI), "--path", str(kb), "crystallize", str(transcript), "--apply", "--dry-run"],
                text=True,
                capture_output=True,
            )
            self.assertNotEqual(conflict.returncode, 0)
            self.assertIn("cannot use --apply and --dry-run together", conflict.stderr)


    def test_relative_source_hash_uses_kb_path_first(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            run_cli("--path", str(kb), "init")
            (kb / "notes.md").write_text("source from kb path\n", encoding="utf-8")
            out = run_cli("--path", str(kb), "source", "add", "notes.md", "--type", "file", "--title", "Notes")
            source = json.loads(out.stdout)
            self.assertEqual(len(source["hash"]), 64)

    def test_crystallize_extracts_structured_session_sections(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            transcript = Path(d) / "structured-session.md"
            transcript.write_text(
                "\n".join([
                    "# Session",
                    "## Decisions",
                    "- Use the JSONL tool server as the adapter boundary.",
                    "## Preferences",
                    "Rohit: Prefer dry-run first writes before apply.",
                    "## Blockers",
                    "Blocker: OPENAI_API_KEY is missing for embeddings.",
                    "## Action Items",
                    "- Update docs/AGENT_FLOW.md and cli/akbp.py.",
                    "## Open Questions",
                    "Question: Should adapters be runtime-specific?",
                    "Files touched: docs/AGENT_FLOW.md, cli/akbp.py",
                ]),
                encoding="utf-8",
            )

            run_cli("--path", str(kb), "init")
            out = run_cli("--path", str(kb), "crystallize", str(transcript))
            data = json.loads(out.stdout)
            summary = data["summary"]
            self.assertIn("Use the JSONL tool server as the adapter boundary.", summary["decisions"])
            self.assertIn("Prefer dry-run first writes before apply.", summary["preferences"])
            self.assertIn("OPENAI_API_KEY is missing for embeddings.", summary["blockers"])
            self.assertIn("Update docs/AGENT_FLOW.md and cli/akbp.py.", summary["actions"])
            self.assertIn("Should adapters be runtime-specific?", summary["questions"])
            self.assertIn("docs/AGENT_FLOW.md", summary["files"])
            self.assertIn("cli/akbp.py", summary["files"])


if __name__ == "__main__":
    unittest.main()
