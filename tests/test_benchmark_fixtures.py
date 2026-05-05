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

    def test_import_safety_fixture_covers_import_check_tool(self):
        path = FIXTURES / "import-safety" / "scenario.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        requests = data["setup"]["tool_server_requests"]
        self.assertEqual(len(requests), 2)
        by_id = {request["id"]: request for request in requests}
        request = by_id["import-check"]
        strict = by_id["import-check-strict"]
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
        export_path = ROOT / request["params"]["file"]
        self.assertTrue(export_path.exists())
        self.assertNotIn("sk-proj-", export_path.read_text(encoding="utf-8"))

    def test_secret_safety_fixture_has_no_real_secret(self):
        path = FIXTURES / "secret-safety" / "scenario.json"
        text = path.read_text(encoding="utf-8")
        self.assertIn("sk-example", text)
        self.assertNotIn("sk-proj-", text)
        self.assertNotIn("xoxb-", text)

    def test_fixture_readme_lists_every_scenario_directory(self):
        readme = (FIXTURES / "README.md").read_text(encoding="utf-8")
        for path in sorted(FIXTURES.glob("*/scenario.json")):
            self.assertIn(f"`{path.parent.name}`", readme)

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
            "review_required",
            "apply_instruction",
            "approved:true",
            "secrets",
        ]:
            self.assertIn(required, text)
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
