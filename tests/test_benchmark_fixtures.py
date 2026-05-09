import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "benchmarks" / "fixtures"
RUNNER = ROOT / "benchmarks" / "run_benchmarks.py"

_spec = importlib.util.spec_from_file_location("akbp_benchmark_runner", RUNNER)
assert _spec and _spec.loader
benchmark_runner = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(benchmark_runner)


class BenchmarkFixtureTest(unittest.TestCase):

    def test_runner_loads_fixture_root_or_scenario_file(self):
        fixture_root = FIXTURES / "preference-recall"
        scenario_file = fixture_root / "scenario.json"
        from_root = benchmark_runner.load_scenarios(fixture_root)
        from_file = benchmark_runner.load_scenarios(scenario_file)
        self.assertEqual(len(from_root), 1)
        self.assertEqual(len(from_file), 1)
        self.assertEqual(from_root[0][1]["id"], "preference-recall-001")
        self.assertEqual(from_file[0][1]["id"], "preference-recall-001")

    def test_benchmark_scenarios_are_well_formed(self):
        scenarios = sorted(FIXTURES.glob("*/scenario.json"))
        self.assertGreaterEqual(len(scenarios), 4)
        for path in scenarios:
            with self.subTest(path=path):
                data = json.loads(path.read_text(encoding="utf-8"))
                self.assertIn("id", data)
                self.assertIn("task", data)
                self.assertIn("setup", data)
                self.assertIn("query", data)
                self.assertIn("expected", data)
                setup = data["setup"]
                self.assertTrue(setup.get("sources") or setup.get("entities") or setup.get("proposed_claims") or setup.get("import_objects") or setup.get("tool_server_requests"))

    def test_graph_jsonl_records_fixture_covers_entities_and_relations(self):
        path = FIXTURES / "graph-jsonl-records" / "scenario.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        setup = data["setup"]
        self.assertEqual(len(setup["entities"]), 2)
        self.assertEqual(setup["relations"][0]["source"], "entity_akbp_protocol")
        self.assertEqual(setup["relations"][0]["target"], "entity_jsonl_tool_server")
        request = setup["tool_server_requests"][0]
        self.assertEqual(request["method"], "akbp.export")
        self.assertEqual(request["expected_result_schema"], "#/$defs/export_result")
        self.assertEqual(request["expected_result_contains"]["entities[].id"], ["entity_akbp_protocol", "entity_jsonl_tool_server"])
        self.assertEqual(request["expected_result_contains"]["relations[].id"], ["relation_protocol_uses_tool_server"])
        self.assertIn("claim_graph_records_export", data["expected"]["must_retrieve"])

    def test_import_apply_malformed_fixture_covers_failure_shape(self):
        path = FIXTURES / "import-apply-malformed" / "scenario.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        request = data["setup"]["tool_server_requests"][0]
        self.assertEqual(request["method"], "akbp.import_apply")
        self.assertEqual(request["expected_result_schema"], "#/$defs/import_apply_result")
        self.assertEqual(request["expected_result_values"]["ok"], False)
        self.assertEqual(request["expected_result_values"]["error_count"], 1)
        self.assertIn("errors[].line", request["expected_result_contains"])
        export_path = ROOT / request["params"]["file"]
        self.assertTrue(export_path.exists())
        self.assertNotIn("sk-proj-", export_path.read_text(encoding="utf-8"))

    def test_import_apply_skipped_existing_fixture_covers_duplicate_reporting(self):
        path = FIXTURES / "import-apply-skipped-existing" / "scenario.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        requests = data["setup"]["tool_server_requests"]
        self.assertEqual(len(requests), 2)
        for request in requests:
            self.assertEqual(request["method"], "akbp.import_apply")
            self.assertEqual(request["expected_result_schema"], "#/$defs/import_apply_result")
            self.assertIn("skipped_existing.sources[]", request["expected_result_contains"])
            self.assertIn("skipped_existing.claims[]", request["expected_result_contains"])
        self.assertEqual(requests[0]["expected_result_contains"]["skipped_existing.sources[]"], ["source_import_apply_existing"])
        export_path = ROOT / requests[0]["params"]["file"]
        self.assertTrue(export_path.exists())
        self.assertNotIn("sk-proj-", export_path.read_text(encoding="utf-8"))

    def test_import_apply_flow_fixture_covers_tool_apply(self):
        path = FIXTURES / "import-apply-flow" / "scenario.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        requests = data["setup"]["tool_server_requests"]
        by_id = {request["id"]: request for request in requests}
        preview = by_id["import-apply-preview"]
        approved = by_id["import-apply-approved"]
        self.assertEqual(preview["method"], "akbp.import_apply")
        self.assertTrue(preview["params"]["dry_run"])
        self.assertFalse(preview["approved"])
        self.assertEqual(preview["expected_result_schema"], "#/$defs/import_apply_result")
        self.assertTrue(approved["approved"])
        self.assertEqual(approved["expected_result_values"]["applied"], True)
        self.assertEqual(preview["expected_result_contains"]["would_write.claims[]"], ["claim_import_apply_fixture"])
        export_path = ROOT / preview["params"]["file"]
        self.assertTrue(export_path.exists())
        self.assertNotIn("sk-proj-", export_path.read_text(encoding="utf-8"))


    def test_unknown_method_rejection_fixture_covers_available_methods(self):
        path = FIXTURES / "unknown-method-rejection" / "scenario.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        request = data["setup"]["tool_server_requests"][0]
        self.assertEqual(request["method"], "akbp.not_supported")
        self.assertEqual(request["expected_error_code"], "unknown_method")
        self.assertEqual(request["expected_error_schema"], "#/$defs/unknown_method_details")
        self.assertIn("available_methods[]", request["expected_error_contains"])
        self.assertIn("akbp.capabilities", request["expected_error_contains"]["available_methods[]"])

    def test_invalid_param_rejection_fixture_covers_param_error_shapes(self):
        path = FIXTURES / "invalid-param-rejection" / "scenario.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        fixture_readme = (FIXTURES / "README.md").read_text(encoding="utf-8")
        self.assertIn("import/export file-param", fixture_readme)
        self.assertIn("source verification id", fixture_readme)
        self.assertIn("claim relation id", fixture_readme)
        requests = {request["id"]: request for request in data["setup"]["tool_server_requests"]}
        self.assertEqual(len(requests), 27)
        self.assertIn("params must be an object", requests["search-params-not-object"]["expected_error_contains"]["type_errors[]"])
        self.assertEqual(requests["search-unknown-param"]["expected_error_schema"], "#/$defs/invalid_params_details")
        self.assertEqual(requests["crystallize-missing-param"]["expected_error_values"]["missing"], ["transcript"])
        self.assertEqual(requests["session-start-limit-range-error"]["method"], "akbp.session.start")
        self.assertIn("limit must be between 1 and 100", requests["session-start-limit-range-error"]["expected_error_contains"]["type_errors[]"])
        self.assertEqual(requests["session-start-limit-range-error"]["expected_error_schema"], "#/$defs/invalid_params_details")
        self.assertEqual(requests["session-end-missing-param"]["method"], "akbp.session.end")
        self.assertEqual(requests["session-end-missing-param"]["expected_error_values"]["missing"], ["transcript"])
        self.assertEqual(requests["session-end-missing-param"]["expected_error_schema"], "#/$defs/invalid_params_details")
        self.assertIn("type_errors[]", requests["search-type-error"]["expected_error_contains"])
        self.assertIn("limit must be an integer", requests["search-type-error"]["expected_error_contains"]["type_errors[]"])
        self.assertIn("query must be at most 4096 characters", requests["search-query-too-long"]["expected_error_contains"]["type_errors[]"])
        self.assertEqual(requests["export-check-file-too-long"]["method"], "akbp.export_check")
        self.assertEqual(requests["import-check-file-too-long"]["method"], "akbp.import_check")
        self.assertEqual(requests["import-apply-file-too-long"]["method"], "akbp.import_apply")
        self.assertIn("file must be at most 4096 characters", requests["export-check-file-too-long"]["expected_error_contains"]["type_errors[]"])
        self.assertIn("file must be at most 4096 characters", requests["import-check-file-too-long"]["expected_error_contains"]["type_errors[]"])
        self.assertIn("file must be at most 4096 characters", requests["import-apply-file-too-long"]["expected_error_contains"]["type_errors[]"])
        self.assertIn("evidence items must be strings", requests["remember-evidence-item-type-error"]["expected_error_contains"]["type_errors[]"])
        self.assertIn("evidence must contain at most 64 items", requests["remember-evidence-count-error"]["expected_error_contains"]["type_errors[]"])
        self.assertIn("evidence[0] must be at most 512 characters", requests["remember-evidence-length-error"]["expected_error_contains"]["type_errors[]"])
        self.assertIn("entity items must be strings", requests["ingest-entity-item-type-error"]["expected_error_contains"]["type_errors[]"])
        self.assertIn("entity[0] must not contain control characters", requests["ingest-entity-control-char-error"]["expected_error_contains"]["type_errors[]"])
        self.assertIn("limit must be between 1 and 100", requests["search-limit-range-error"]["expected_error_contains"]["type_errors[]"])
        self.assertEqual(requests["audit-limit-type-error"]["method"], "akbp.audit")
        self.assertEqual(requests["audit-limit-range-error"]["method"], "akbp.audit")
        self.assertIn("limit must be an integer", requests["audit-limit-type-error"]["expected_error_contains"]["type_errors[]"])
        self.assertIn("limit must be between 1 and 100", requests["audit-limit-range-error"]["expected_error_contains"]["type_errors[]"])
        self.assertIn("confidence must be between 0 and 1", requests["ingest-confidence-range-error"]["expected_error_contains"]["type_errors[]"])
        self.assertIn("type must be one of: decision, fact, observation, preference, question, warning, workflow", requests["remember-type-enum-error"]["expected_error_contains"]["type_errors[]"])
        self.assertIn("type must be one of: audio, commit, file, folder, issue, message, pdf, screenshot, transcript, url, video", requests["source-type-enum-error"]["expected_error_contains"]["type_errors[]"])
        self.assertEqual(requests["source-verify-source-id-too-long"]["method"], "akbp.source.verify")
        self.assertEqual(requests["source-verify-source-id-control-char"]["method"], "akbp.source.verify")
        self.assertIn("source_id must be at most 512 characters", requests["source-verify-source-id-too-long"]["expected_error_contains"]["type_errors[]"])
        self.assertIn("source_id must not contain control characters", requests["source-verify-source-id-control-char"]["expected_error_contains"]["type_errors[]"])
        self.assertEqual(requests["supersede-old-claim-id-too-long"]["method"], "akbp.supersede")
        self.assertEqual(requests["contradict-source-claim-id-control-char"]["method"], "akbp.contradict")
        self.assertEqual(requests["contradict-target-claim-id-too-long"]["method"], "akbp.contradict")
        self.assertIn("old_claim_id must be at most 512 characters", requests["supersede-old-claim-id-too-long"]["expected_error_contains"]["type_errors[]"])
        self.assertIn("source_claim_id must not contain control characters", requests["contradict-source-claim-id-control-char"]["expected_error_contains"]["type_errors[]"])
        self.assertIn("target_claim_id must be at most 512 characters", requests["contradict-target-claim-id-too-long"]["expected_error_contains"]["type_errors[]"])
        self.assertIn("claim_type must be one of: decision, fact, observation, preference, question, warning, workflow", requests["ingest-claim-type-enum-error"]["expected_error_contains"]["type_errors[]"])

    def test_import_compatibility_edges_fixture_rejects_bad_shapes(self):
        path = FIXTURES / "import-compatibility-edges" / "scenario.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        requests = {request["id"]: request for request in data["setup"]["tool_server_requests"]}
        mixed = requests["import-check-mixed"]
        self.assertEqual(mixed["method"], "akbp.import_check")
        self.assertEqual(mixed["expected_result_values"]["checked"], 11)
        self.assertEqual(mixed["expected_result_values"]["accepted_count"], 2)
        self.assertEqual(mixed["expected_result_values"]["rejected_count"], 9)
        self.assertIn("claim_import_compat_bad_evidence_item", mixed["expected_result_contains"]["rejected[].id"])
        self.assertIn("claim_import_compat_evidence_not_list", mixed["expected_result_contains"]["rejected[].id"])
        self.assertIn("claim_import_compat_entity_too_long", mixed["expected_result_contains"]["rejected[].id"])
        self.assertIn("claim_import_compat_entities_not_list", mixed["expected_result_contains"]["rejected[].id"])
        self.assertIn("claim_import_compat_supersedes_not_list", mixed["expected_result_contains"]["rejected[].id"])
        self.assertIn("claim_import_compat_valid", mixed["expected_result_contains"]["rejected[].id"])
        self.assertIn("claim claim_import_compat_bad_evidence_item evidence items must be strings", mixed["expected_result_contains"]["rejected[].reason"])
        self.assertIn("claim claim_import_compat_evidence_not_list evidence must be a list", mixed["expected_result_contains"]["rejected[].reason"])
        self.assertIn("claim claim_import_compat_entity_too_long entities[0] must be at most 256 characters", mixed["expected_result_contains"]["rejected[].reason"])
        self.assertIn("claim claim_import_compat_entities_not_list entities must be a list of strings", mixed["expected_result_contains"]["rejected[].reason"])
        self.assertIn("claim claim_import_compat_supersedes_not_list supersedes must be a list of strings", mixed["expected_result_contains"]["rejected[].reason"])
        self.assertIn("duplicate import id: claim_import_compat_valid", mixed["expected_result_contains"]["rejected[].reason"])
        export_path = ROOT / mixed["params"]["file"]
        self.assertTrue(export_path.exists())
        export_text = export_path.read_text(encoding="utf-8")
        self.assertIn('"evidence":[42]', export_text)
        self.assertIn('"evidence":"source_import_compat_edge"', export_text)
        self.assertIn('"entities":"agent"', export_text)
        self.assertIn('"supersedes":"claim_import_compat_valid"', export_text)
        self.assertIn('"id":"claim_import_compat_valid"', export_text)

    def test_import_safety_fixture_covers_import_check_tool(self):
        path = FIXTURES / "import-safety" / "scenario.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        requests = data["setup"]["tool_server_requests"]
        self.assertEqual(len(requests), 3)
        by_id = {request["id"]: request for request in requests}
        request = by_id["import-check"]
        strict = by_id["import-check-strict"]
        rejected_apply = by_id["import-apply-rejected-preview"]
        self.assertEqual(request["method"], "akbp.import_check")
        self.assertEqual(strict["method"], "akbp.import_check")
        self.assertEqual(request["expected_result_schema"], "#/$defs/import_check_result")
        self.assertEqual(strict["expected_result_schema"], "#/$defs/import_check_result")
        self.assertIn("accepted", request["expected_result_fields"])
        self.assertIn("accepted_count", request["expected_result_fields"])
        self.assertIn("rejected", request["expected_result_fields"])
        self.assertIn("rejected_count", request["expected_result_fields"])
        self.assertEqual(request["expected_result_values"]["checked"], 3)
        self.assertEqual(request["expected_result_values"]["accepted_count"], 1)
        self.assertEqual(request["expected_result_values"]["rejected_count"], 2)
        self.assertEqual(request["expected_result_values"]["fail_on_rejected"], False)
        self.assertEqual(strict["expected_result_values"]["ok"], False)
        self.assertEqual(strict["expected_result_values"]["fail_on_rejected"], True)
        self.assertEqual(request["expected_result_contains"]["accepted[].id"], ["claim_imported_safe_blocker"])
        self.assertEqual(request["expected_result_contains"]["rejected[].id"], ["source_imported_terminal_log", "claim_imported_deploy_blocker"])
        self.assertEqual(strict["expected_result_contains"], request["expected_result_contains"])
        self.assertEqual(rejected_apply["method"], "akbp.import_apply")
        self.assertEqual(rejected_apply["expected_result_schema"], "#/$defs/import_apply_result")
        self.assertEqual(rejected_apply["expected_result_values"]["ok"], False)
        self.assertEqual(rejected_apply["expected_result_values"]["rejected_count"], 2)
        self.assertIn("would_write", rejected_apply["expected_result_fields"])
        self.assertIn("skipped_existing", rejected_apply["expected_result_fields"])
        export_path = ROOT / request["params"]["file"]
        self.assertTrue(export_path.exists())
        self.assertNotIn("sk-proj-", export_path.read_text(encoding="utf-8"))

    def test_secret_safety_fixture_has_no_real_secret(self):
        path = FIXTURES / "secret-safety" / "scenario.json"
        text = path.read_text(encoding="utf-8")
        self.assertIn("sk-example", text)
        self.assertNotIn("sk-proj-", text)
        self.assertNotIn("xoxb-", text)
        data = json.loads(text)
        request = data["setup"]["tool_server_requests"][0]
        self.assertEqual(request["method"], "akbp.source.add")
        self.assertEqual(request["expected_result_values"]["title"], "Terminal output [REDACTED]")
        self.assertIn("title", request["expected_result_fields"])
        self.assertEqual(request["expected_result_schema"], "#/$defs/source_result")

    def test_fixture_readme_lists_every_scenario_directory(self):
        readme = (FIXTURES / "README.md").read_text(encoding="utf-8")
        for path in sorted(FIXTURES.glob("*/scenario.json")):
            self.assertIn(f"`{path.parent.name}`", readme)
        self.assertIn("scalar collection-field rejection", readme)

    def test_search_index_observability_fixture_covers_prefix_and_index_keys(self):
        path = FIXTURES / "search-index-observability" / "scenario.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        by_method = {request["method"]: request for request in data["setup"]["tool_server_requests"]}
        index = by_method["akbp.index"]
        self.assertTrue(index["approved"])
        self.assertEqual(index["expected_result_schema"], "#/$defs/index_result")
        self.assertIn("indexed_keys", index["expected_result_fields"])
        self.assertIn("skipped_keys", index["expected_result_fields"])
        self.assertIn("removed_keys", index["expected_result_fields"])
        search = by_method["akbp.search"]
        self.assertEqual(search["params"]["query"], "pref* AND index*")
        self.assertEqual(search["expected_result_values"]["fts_query"], "pref* AND index*")
        self.assertEqual(search["expected_result_schema"], "#/$defs/search_result")

    def test_search_query_compatibility_fixture_covers_empty_fts_queries(self):
        path = FIXTURES / "search-query-compatibility" / "scenario.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        requests = {request["id"]: request for request in data["setup"]["tool_server_requests"]}
        for request_id in ["leading-not-empty-search", "punctuation-empty-search", "operator-only-empty-search"]:
            request = requests[request_id]
            self.assertEqual(request["method"], "akbp.search")
            self.assertEqual(request["expected_result_schema"], "#/$defs/search_result")
            self.assertEqual(request["expected_result_values"]["backend"], "sqlite_fts5")
            self.assertEqual(request["expected_result_values"]["fts_query"], "")
            self.assertEqual(request["expected_result_values"]["results"], [])
        mixed = requests["mixed-operator-prefix-search"]
        self.assertEqual(mixed["expected_result_values"]["fts_query"], '"JSONL" AND tool* OR Python*')
        self.assertEqual(mixed["expected_result_contains"]["results[].id"], ["claim_search_query_compat"])
        dangling = requests["dangling-operator-search"]
        self.assertEqual(dangling["expected_result_values"]["fts_query"], '"JSONL"')
        self.assertEqual(dangling["expected_result_contains"]["results[].id"], ["claim_search_query_compat"])


    def test_session_crystallization_fixture_requires_context_citations(self):
        path = FIXTURES / "session-crystallization" / "scenario.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["expected"]["must_cite_in_context"], ["source_structured_session_001", "source_agent_flow_doc"])
        report = benchmark_runner.score_real_akbp(data)
        self.assertTrue(report["ok"], report)
        self.assertIn("source_structured_session_001", report["context_citation_ids"])
        self.assertIn("source_agent_flow_doc", report["context_citation_ids"])

    def test_write_preview_crystallize_fixture_covers_schema_refs(self):
        path = FIXTURES / "write-preview-crystallize-schema" / "scenario.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        by_method = {request["method"]: request for request in data["setup"]["tool_server_requests"]}
        by_id = {request["id"]: request for request in data["setup"]["tool_server_requests"]}
        self.assertEqual(by_id["ingest-preview"]["expected_result_schema"], "#/$defs/ingest_dry_run_result")
        self.assertTrue(by_id["ingest-preview"]["params"]["dry_run"])
        self.assertEqual(by_id["ingest-apply"]["expected_result_schema"], "#/$defs/ingest_result")
        self.assertTrue(by_id["ingest-apply"]["approved"])
        self.assertEqual(by_id["crystallize-apply"]["expected_result_schema"], "#/$defs/crystallize_session_result")
        self.assertTrue(by_id["crystallize-apply"]["approved"])
        self.assertIn("claim_ingest_preview_is_schema_backed", data["expected"]["must_retrieve"])
        self.assertIn("claim_ingest_apply_is_schema_backed", data["expected"]["must_retrieve"])
        self.assertIn("claim_crystallize_apply_is_schema_backed", data["expected"]["must_retrieve"])


    def test_retrieval_ambiguity_ranking_fixture_covers_lifecycle_context(self):
        path = FIXTURES / "retrieval-ambiguity-ranking" / "scenario.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertIn("claim_adapter_lifecycle_uses_session_methods", data["expected"]["must_retrieve"])
        self.assertIn("claim_validation_keeps_adapter_flow_green", data["expected"]["must_retrieve"])
        self.assertIn("source_runtime_adapter_notes", data["expected"]["must_cite"])
        self.assertIn("source_validation_notes", data["expected"]["must_cite_in_context"])

    def test_retrieval_noisy_evidence_fixture_covers_direct_cited_claims(self):
        path = FIXTURES / "retrieval-noisy-evidence" / "scenario.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertIn("claim_shutdown_writes_require_review_gate", data["expected"]["must_retrieve"])
        self.assertIn("source_adapter_shutdown_checklist", data["expected"]["must_cite_in_context"])
        self.assertEqual(len(data["setup"]["claims"]), 4)
        report = benchmark_runner.score_real_akbp(data)
        self.assertTrue(report["ok"], report)
        self.assertIn("claim_shutdown_writes_require_review_gate", report["query_result_ids"])
        self.assertIn("source_adapter_shutdown_checklist", report["context_citation_ids"])

    def test_retrieval_citation_bundle_fixture_covers_context_and_cite(self):
        path = FIXTURES / "retrieval-citation-bundle" / "scenario.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        requests = {request["id"]: request for request in data["setup"]["tool_server_requests"]}
        context = requests["context-release-rollback"]
        cite = requests["cite-release-rollback"]
        self.assertEqual(context["method"], "akbp.context")
        self.assertEqual(context["expected_result_schema"], "#/$defs/context_result")
        self.assertEqual(context["expected_result_contains"]["items[].id"], ["claim_release_needs_rollback_owner"])
        self.assertEqual(cite["method"], "akbp.cite")
        self.assertEqual(cite["expected_result_schema"], "#/$defs/cite_result")
        self.assertEqual(cite["expected_result_contains"]["evidence[]"], ["source_release_risk_note", "source_operator_review"])
        self.assertEqual(data["expected"]["must_cite"], ["source_release_risk_note", "source_operator_review"])

    def test_read_method_schema_fixture_covers_read_responses(self):
        path = FIXTURES / "read-method-schema" / "scenario.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        by_method = {request["method"]: request for request in data["setup"]["tool_server_requests"]}
        expected = {
            "akbp.capabilities": "#/$defs/capabilities_result",
            "akbp.status": "#/$defs/status_result",
            "akbp.context": "#/$defs/context_result",
            "akbp.search": "#/$defs/search_result",
            "akbp.cite": "#/$defs/cite_result",
            "akbp.export": "#/$defs/export_result",
            "akbp.audit": "#/$defs/audit_result",
        }
        self.assertEqual(set(by_method), set(expected))
        for method, schema_ref in expected.items():
            self.assertFalse(by_method[method]["approved"])
            self.assertEqual(by_method[method]["expected_result_schema"], schema_ref)
        self.assertIn("claim_read_methods_are_schema_backed", data["expected"]["must_retrieve"])


    def test_capability_negotiation_fixture_covers_method_policy(self):
        path = FIXTURES / "capability-negotiation" / "scenario.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        request = data["setup"]["tool_server_requests"][0]
        self.assertEqual(request["method"], "akbp.capabilities")
        self.assertEqual(request["expected_result_schema"], "#/$defs/capabilities_result")
        expected = request["expected_result_contains"]
        self.assertIn("features.method_param_schemas", expected)
        self.assertIn("methods.akbp\\.remember.review_required", expected)
        self.assertIn("methods.akbp\\.remember.params[]", expected)

    def test_read_method_schema_fixture_covers_capability_enforcement_flags(self):
        path = FIXTURES / "read-method-schema" / "scenario.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        capabilities = data["setup"]["tool_server_requests"][0]
        self.assertEqual(capabilities["id"], "capabilities-read")
        contains = capabilities["expected_result_contains"]
        self.assertEqual(contains["features.method_param_schemas"], [True])
        self.assertEqual(contains["features.unknown_param_rejection"], [True])
        self.assertEqual(contains["features.required_param_validation"], [True])
        self.assertEqual(contains["features.approval_required_errors"], [True])
        self.assertIn("methods.akbp\\.search.params_schema", contains)
        self.assertIn("methods.akbp\\.import_apply.params_schema", contains)

    def test_review_gated_writes_fixture_covers_review_metadata(self):
        path = FIXTURES / "review-gated-writes" / "scenario.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        text = json.dumps(data)
        self.assertIn("review_required", text)
        self.assertIn("apply_instruction", text)
        self.assertIn("approval", text)
        self.assertIn("claim_agents_must_not_apply_without_review", data["expected"]["must_retrieve"])
        self.assertEqual(set(data["expected"]["must_dry_run_tool_methods"]), {
            "akbp.remember",
            "akbp.source.add",
            "akbp.supersede",
            "akbp.contradict",
        })
        for request in data["setup"]["tool_server_requests"]:
            self.assertTrue(request["params"]["dry_run"])
            self.assertEqual(request["expected_result_schema"], "#/$defs/dry_run_review_result")
            self.assertEqual(request["expected_result_values"]["review_required"], True)
            self.assertIn("apply_instruction", request["expected_result_fields"])

    def test_approved_write_apply_fixture_covers_all_write_shapes(self):
        path = FIXTURES / "approved-write-apply" / "scenario.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(set(data["expected"]["must_apply_tool_methods"]), {
            "akbp.remember",
            "akbp.source.add",
            "akbp.supersede",
            "akbp.contradict",
        })
        by_method = {request["method"]: request for request in data["setup"]["tool_server_requests"]}
        self.assertIn("text", by_method["akbp.remember"]["expected_result_fields"])
        self.assertEqual(by_method["akbp.remember"]["expected_result_schema"], "#/$defs/claim_result")
        self.assertIn("locator", by_method["akbp.source.add"]["expected_result_fields"])
        self.assertEqual(by_method["akbp.source.add"]["expected_result_schema"], "#/$defs/source_result")
        self.assertIn("supersedes", by_method["akbp.supersede"]["expected_result_fields"])
        self.assertEqual(by_method["akbp.supersede"]["expected_result_schema"], "#/$defs/claim_result")
        self.assertIn("relation", by_method["akbp.contradict"]["expected_result_fields"])
        self.assertEqual(by_method["akbp.contradict"]["expected_result_schema"], "#/$defs/relation_result")
        self.assertTrue(all(request["approved"] for request in data["setup"]["tool_server_requests"]))

    def test_unapproved_write_rejection_fixture_covers_all_write_errors(self):
        path = FIXTURES / "unapproved-write-rejection" / "scenario.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(set(data["expected"]["must_reject_tool_methods"]), {
            "akbp.remember",
            "akbp.source.add",
            "akbp.supersede",
            "akbp.contradict",
            "akbp.import_apply",
            "akbp.crystallize_session",
            "akbp.session.end",
        })
        for request in data["setup"]["tool_server_requests"]:
            self.assertFalse(request["approved"])
            self.assertEqual(request["expected_error_code"], "approval_required")
            self.assertEqual(request["expected_error_schema"], "#/$defs/approval_required_details")
            self.assertIn("review_required", request["expected_error_fields"])
            self.assertIn("apply_instruction", request["expected_error_fields"])
            self.assertEqual(request["expected_error_values"]["method"], request["method"])
            self.assertEqual(request["expected_error_values"]["dry_run"], False)
            self.assertEqual(request["expected_error_values"]["review_required"], True)

    def test_runner_validates_expected_error_schema_refs(self):
        data = {
            "id": "bad-error-schema-ref",
            "task": "Reject fixture error schema refs that do not map to response schema defs.",
            "setup": {
                "tool_server_requests": [
                    {
                        "id": "bad-error",
                        "method": "akbp.remember",
                        "params": {"text": "x"},
                        "expected_error_code": "approval_required",
                        "expected_error_fields": ["method"],
                        "expected_error_schema": "#/$defs/not_real",
                    }
                ]
            },
            "query": "x",
            "expected": {},
        }
        issues = benchmark_runner.check_scenario(data)
        self.assertTrue(any("invalid expected_error_schema" in issue for issue in issues))

    def test_runner_validates_expected_result_schema_refs(self):
        data = {
            "id": "bad-schema-ref",
            "task": "Reject fixture schema refs that do not map to response schema defs.",
            "setup": {
                "tool_server_requests": [
                    {
                        "id": "bad-request",
                        "method": "akbp.remember",
                        "params": {"text": "x"},
                        "expected_result_fields": ["id"],
                        "expected_result_schema": "#/$defs/not_real",
                    }
                ]
            },
            "query": "x",
            "expected": {},
        }
        issues = benchmark_runner.check_scenario(data)
        self.assertTrue(any("invalid expected_result_schema" in issue for issue in issues))

    def test_runner_checks_nested_expected_contains(self):
        payload = {
            "entities": [{"id": "entity_one"}, {"id": "entity_two"}],
            "relations": [{"id": "relation_one"}],
        }
        self.assertEqual(benchmark_runner.missing_nested_contains(payload, {"entities[].id": ["entity_one"]}), {})
        self.assertEqual(
            benchmark_runner.missing_nested_contains(payload, {"relations[].id": ["missing_relation"]}),
            {"relations[].id": ["missing_relation"]},
        )

    def test_runner_schema_shape_checks_nested_items(self):
        payload = {
            "query": "schema",
            "generated_at": "2026-01-01T00:00:00Z",
            "items": [
                {
                    "id": "claim_1",
                    "type": "claim",
                    "text": "Nested schema checks should reject extra fields.",
                    "score": 1.0,
                    "evidence": [],
                    "extra": "not allowed",
                }
            ],
            "warnings": [],
        }
        issues = benchmark_runner.schema_shape_issues(payload, benchmark_runner.schema_def("#/$defs/context_result"))
        self.assertIn("$.items[0] unexpected field extra", issues)

    def test_runner_rejects_undocumented_expected_value_fields(self):
        data = {
            "id": "bad-tool-contract",
            "task": "Reject incomplete tool-server expected value contracts.",
            "setup": {
                "tool_server_requests": [
                    {
                        "id": "bad-request",
                        "method": "akbp.remember",
                        "params": {"text": "x"},
                        "expected_result_fields": ["dry_run"],
                        "expected_result_values": {"review_required": True},
                    },
                    {
                        "id": "bad-error",
                        "method": "akbp.remember",
                        "params": {"text": "x"},
                        "expected_error_code": "approval_required",
                        "expected_error_fields": ["method"],
                        "expected_error_values": {"dry_run": False},
                    },
                ]
            },
            "query": "x",
            "expected": {},
        }
        issues = benchmark_runner.check_scenario(data)
        self.assertIn("tool request bad-request expected_result_values field review_required must also be listed in expected_result_fields", issues)
        self.assertIn("tool request bad-error expected_error_values field dry_run must also be listed in expected_error_fields", issues)

    def test_adapter_write_safety_fixture_covers_approval_policy(self):
        path = FIXTURES / "adapter-write-safety" / "scenario.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        text = json.dumps(data)
        for required in [
            "dry_run_first",
            "require_review_metadata",
            "apply_requires_approved",
            "akbp.session.end",
            "review_required",
            "apply_instruction",
            "approved:true",
            "secrets",
        ]:
            self.assertIn(required, text)
        self.assertNotIn("akbp.crystallize_session", text)
        self.assertIn("claim_adapter_docs_require_review_boundary", data["expected"]["must_retrieve"])

    def test_benchmark_runner_passes(self):
        proc = subprocess.run([sys.executable, str(RUNNER), "--akbp"], text=True, capture_output=True, check=True)
        report = json.loads(proc.stdout)
        self.assertTrue(report["ok"])
        self.assertEqual(report["mode"], "akbp-score")
        self.assertGreaterEqual(report["count"], 4)
        self.assertTrue(all("score" in item for item in report["results"]))
        scored = [item for item in report["results"] if "akbp" in item["score"] and not item["score"]["akbp"].get("skipped")]
        self.assertTrue(scored)
        by_id = {item["id"]: item for item in report["results"]}
        approved_checks = by_id["approved-write-apply-001"]["score"]["akbp"]["checks"]
        rejected_checks = by_id["unapproved-write-rejection-001"]["score"]["akbp"]["checks"]
        dry_run_checks = by_id["review-gated-writes-001"]["score"]["akbp"]["checks"]
        self.assertTrue(any(check["name"] == "akbp_tool_apply_response_shape" and check["ok"] for check in approved_checks))
        self.assertTrue(any(check["name"] == "akbp_tool_rejection_shape" and check["ok"] for check in rejected_checks))
        self.assertTrue(any(check["name"] == "akbp_tool_apply_response_shape" and check["ok"] for check in dry_run_checks))


if __name__ == "__main__":
    unittest.main()
