import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "cli" / "akbp.py"
SERVER = ROOT / "tool-server" / "akbp_tool_server.py"
INSTALLED_SERVER = ROOT / "cli" / "akbp_tool_server.py"


def run_cli(*args):
    return subprocess.run([sys.executable, str(CLI), *args], text=True, capture_output=True, check=True)


def schema_def(name):
    schema = json.loads((ROOT / "schemas" / "tool-response.schema.json").read_text(encoding="utf-8"))
    return schema["$defs"][name]


def load_server_module():
    spec = importlib.util.spec_from_file_location("akbp_tool_server_reference", SERVER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_cli_module():
    spec = importlib.util.spec_from_file_location("akbp_cli_reference", CLI)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def assert_matches_required_schema(testcase, payload, schema):
    for field in schema["required"]:
        testcase.assertIn(field, payload)
    for field, spec in schema["properties"].items():
        if field not in payload:
            continue
        if "const" in spec:
            testcase.assertEqual(payload[field], spec["const"])
        expected_type = spec.get("type")
        if expected_type == "string":
            testcase.assertIsInstance(payload[field], str)
            if spec.get("minLength"):
                testcase.assertGreaterEqual(len(payload[field]), spec["minLength"])
        elif expected_type == "object":
            testcase.assertIsInstance(payload[field], dict)
        elif expected_type == "array":
            testcase.assertIsInstance(payload[field], list)
        elif expected_type == "boolean":
            testcase.assertIsInstance(payload[field], bool)
        elif expected_type == "integer":
            testcase.assertIsInstance(payload[field], int)
            if "minimum" in spec:
                testcase.assertGreaterEqual(payload[field], spec["minimum"])
        elif expected_type == "number":
            testcase.assertIsInstance(payload[field], (int, float))


def assert_response_envelope(testcase, payload):
    testcase.assertEqual(set(payload), {"id", "ok", "result", "error"})
    testcase.assertIsInstance(payload["ok"], bool)
    if payload["ok"]:
        testcase.assertIsNone(payload["error"])
    else:
        testcase.assertIsNone(payload["result"])
        testcase.assertIsInstance(payload["error"], dict)
        testcase.assertIn("code", payload["error"])
        testcase.assertIn("message", payload["error"])
        testcase.assertIsInstance(payload["error"]["code"], str)
        testcase.assertIsInstance(payload["error"]["message"], str)


class ToolServerTest(unittest.TestCase):

    def test_context_budget_reports_clipped_and_omitted_items(self):
        cli = load_cli_module()
        pack = {
            "query": "adapter startup",
            "generated_at": "2026-01-01T00:00:00Z",
            "items": [
                {"id": "claim-one", "summary": "abcde", "citations": ["source-one"]},
                {"id": "claim-two", "summary": "vwxyz", "citations": ["source-two"]},
            ],
            "warnings": [],
        }

        result = cli.apply_context_budget(pack, 3)

        self.assertEqual(result["items"][0]["summary"], "abc")
        self.assertEqual(len(result["items"]), 1)
        self.assertEqual(result["budget"]["summary_chars"], 3)
        self.assertEqual(result["budget"]["original_summary_chars"], 10)
        self.assertEqual(result["budget"]["clipped_items"], 1)
        self.assertEqual(result["budget"]["omitted_items"], 1)
        self.assertEqual(result["budget"]["truncated_items"], 2)
        self.assertEqual(result["budget"]["items_before_budget"], 2)
        self.assertEqual(result["budget"]["items_after_budget"], 1)
        self.assertIn("Context budget truncated: clipped 1 item(s) and omitted 1 item(s)", result["warnings"][0])

    def test_all_server_outputs_use_response_envelope(self):
        requests = "\n".join([
            json.dumps({"id": "caps", "method": "akbp.capabilities"}),
            json.dumps({"id": "status", "method": "akbp.status"}),
            json.dumps({"id": "bad", "method": "akbp.missing"}),
            json.dumps({"method": "akbp.status"}),
            json.dumps({"id": "extra", "method": "akbp.status", "unexpected": True}),
            json.dumps({"id": "bad-params", "method": "akbp.search", "params": {"query": 123}}),
            "not-json",
        ]) + "\n"
        proc = subprocess.run([sys.executable, str(SERVER)], input=requests, text=True, capture_output=True, check=True)
        lines = [json.loads(line) for line in proc.stdout.splitlines()]
        self.assertEqual(len(lines), 7)
        for line in lines:
            with self.subTest(response=line):
                assert_response_envelope(self, line)
        self.assertEqual(lines[0]["error"], None)
        self.assertEqual(lines[2]["error"]["code"], "unknown_method")
        self.assertEqual(lines[3]["error"]["code"], "invalid_request")
        self.assertEqual(lines[4]["error"]["code"], "invalid_request")
        self.assertIn("unknown request field", " ".join(lines[4]["error"]["details"]["errors"]))
        self.assertEqual(lines[5]["error"]["code"], "invalid_params")
        self.assertEqual(lines[6]["error"]["code"], "invalid_json")
        assert_matches_required_schema(self, lines[2]["error"]["details"], schema_def("unknown_method_details"))
        assert_matches_required_schema(self, lines[3]["error"]["details"], schema_def("invalid_request_details"))
        assert_matches_required_schema(self, lines[4]["error"]["details"], schema_def("invalid_request_details"))
        assert_matches_required_schema(self, lines[5]["error"]["details"], schema_def("invalid_params_details"))
        assert_matches_required_schema(self, lines[6]["error"]["details"], schema_def("invalid_json_details"))
        self.assertIn("tool-request.schema.json", lines[6]["error"]["details"]["schema"])


    def test_non_object_json_requests_return_schema_backed_errors(self):
        requests = '\n'.join([
            '[]',
            '"string"',
            '42',
            'true',
        ]) + '\n'
        proc = subprocess.run([sys.executable, str(SERVER)], input=requests, text=True, capture_output=True, check=True)
        lines = [json.loads(line) for line in proc.stdout.splitlines()]
        self.assertEqual(len(lines), 4)
        for line in lines:
            with self.subTest(line=line):
                assert_response_envelope(self, line)
                self.assertFalse(line["ok"])
                self.assertEqual(line["id"], None)
                self.assertEqual(line["error"]["code"], "invalid_request")
                self.assertEqual(line["error"]["message"], "request must be a JSON object")
                self.assertEqual(line["error"]["details"]["errors"], ["request must be a JSON object"])
                self.assertIn("tool-request.schema.json", line["error"]["details"]["schema"])
                assert_matches_required_schema(self, line["error"]["details"], schema_def("invalid_request_details"))

    def test_request_schema_documents_runtime_envelope_guards(self):
        schema = json.loads((ROOT / "schemas" / "tool-request.schema.json").read_text(encoding="utf-8"))
        id_schema = schema["properties"]["id"]
        self.assertEqual(id_schema["maxLength"], 512)
        self.assertEqual(id_schema["minimum"], -9007199254740991)
        self.assertEqual(id_schema["maximum"], 9007199254740991)
        self.assertEqual(id_schema["pattern"], "^[^\\u0000\\n\\r]*$")
        path_schema = schema["properties"]["path"]
        self.assertEqual(path_schema["minLength"], 1)
        self.assertEqual(path_schema["maxLength"], 4096)
        self.assertEqual(path_schema["pattern"], "^[^\\u0000\\n\\r]*$")

    def test_server_rejects_unsafe_request_paths_before_dispatch(self):
        requests = "\n".join([
            json.dumps({"id": "empty", "path": "", "method": "akbp.status"}),
            json.dumps({"id": "control", "path": "kb\nother", "method": "akbp.status"}),
            json.dumps({"id": "long", "path": "a" * 4097, "method": "akbp.status"}),
        ]) + "\n"
        proc = subprocess.run([sys.executable, str(SERVER)], input=requests, text=True, capture_output=True, check=True)
        lines = [json.loads(line) for line in proc.stdout.splitlines()]
        self.assertEqual(len(lines), 3)
        for line in lines:
            with self.subTest(line=line):
                assert_response_envelope(self, line)
                self.assertFalse(line["ok"])
                self.assertEqual(line["error"]["code"], "invalid_request")
                self.assertIn("path", " ".join(line["error"]["details"]["errors"]))

    def test_server_rejects_unsafe_request_ids_before_output(self):
        requests = "\n".join([
            '{"id":1e999,"method":"akbp.status"}',
            json.dumps({"id": "line\nbreak", "method": "akbp.status"}),
            json.dumps({"id": "x" * 513, "method": "akbp.status"}),
            json.dumps({"id": 9007199254740992, "method": "akbp.status"}),
        ]) + "\n"
        proc = subprocess.run([sys.executable, str(SERVER)], input=requests, text=True, capture_output=True, check=True)
        self.assertNotIn("Infinity", proc.stdout)
        lines = [json.loads(line) for line in proc.stdout.splitlines()]
        self.assertEqual(len(lines), 4)
        expected = ["finite string or number", "control characters", "512 characters", "9007199254740991"]
        for line, message in zip(lines, expected):
            with self.subTest(line=line):
                assert_response_envelope(self, line)
                self.assertIsNone(line["id"])
                self.assertFalse(line["ok"])
                self.assertEqual(line["error"]["code"], "invalid_request")
                self.assertIn(message, " ".join(line["error"]["details"]["errors"]))

    def test_server_rejects_non_object_params_before_dispatch(self):
        requests = "\n".join([
            json.dumps({"id": "null", "method": "akbp.status", "params": None}),
            json.dumps({"id": "array", "method": "akbp.status", "params": []}),
            json.dumps({"id": "false", "method": "akbp.status", "params": False}),
            json.dumps({"id": "string", "method": "akbp.status", "params": ""}),
        ]) + "\n"
        proc = subprocess.run([sys.executable, str(SERVER)], input=requests, text=True, capture_output=True, check=True)
        lines = [json.loads(line) for line in proc.stdout.splitlines()]
        self.assertEqual(len(lines), 4)
        for line in lines:
            with self.subTest(line=line):
                assert_response_envelope(self, line)
                self.assertFalse(line["ok"])
                self.assertEqual(line["error"]["code"], "invalid_params")
                self.assertEqual(line["error"]["details"]["type_errors"], ["params must be an object"])
                self.assertTrue(line["error"]["details"]["params_schema"].endswith("#/$defs/akbp.status.params"))

    def test_capabilities_negotiates_required_profiles(self):
        requests = json.dumps({
            "id": "caps",
            "method": "akbp.capabilities",
            "params": {
                "client": "profile-negotiation-test",
                "requires": ["method_param_schemas", "features.capability_negotiation"],
                "requires_profiles": ["read_only", "missing_profile"],
                "requires_methods": ["akbp.context", "akbp.future"],
            },
        }) + "\n"
        proc = subprocess.run([sys.executable, str(SERVER)], input=requests, text=True, capture_output=True, check=True)
        line = json.loads(proc.stdout)
        assert_response_envelope(self, line)
        negotiation = line["result"]["negotiation"]
        self.assertEqual(negotiation["client"], "profile-negotiation-test")
        self.assertEqual(negotiation["supported_features"], ["method_param_schemas", "features.capability_negotiation"])
        self.assertEqual(negotiation["unsupported_features"], [])
        self.assertEqual(negotiation["supported_profiles"], ["read_only"])
        self.assertEqual(negotiation["unsupported_profiles"], ["missing_profile"])
        self.assertEqual(negotiation["supported_methods"], ["akbp.context"])
        self.assertEqual(negotiation["unsupported_methods"], ["akbp.future"])
        self.assertFalse(negotiation["satisfied"])

    def test_capabilities_rejects_invalid_required_profiles_param(self):
        requests = json.dumps({
            "id": "bad-profiles",
            "method": "akbp.capabilities",
            "params": {"requires_profiles": "read_only"},
        }) + "\n"
        proc = subprocess.run([sys.executable, str(SERVER)], input=requests, text=True, capture_output=True, check=True)
        line = json.loads(proc.stdout)
        assert_response_envelope(self, line)
        self.assertFalse(line["ok"])
        self.assertEqual(line["error"]["code"], "invalid_params")
        self.assertIn("requires_profiles must be an array", line["error"]["details"]["type_errors"])

    def test_server_rejects_oversized_request_lines_before_json_parse(self):
        request = " " * (1048576 + 1) + "\n"
        proc = subprocess.run([sys.executable, str(SERVER)], input=request, text=True, capture_output=True, check=True)
        line = json.loads(proc.stdout)
        assert_response_envelope(self, line)
        self.assertFalse(line["ok"])
        self.assertEqual(line["error"]["code"], "invalid_request")
        self.assertIn("max_request_bytes", line["error"]["message"])
        self.assertIn("tool-request.schema.json", line["error"]["details"]["schema"])

    def test_server_rejects_non_standard_json_constants(self):
        requests = "\n".join([
            '{"id":"nan","method":"akbp.status","params":{"limit":NaN}}',
            '{"id":"inf","method":"akbp.status","params":{"limit":Infinity}}',
            '{"id":"neg-inf","method":"akbp.status","params":{"limit":-Infinity}}',
        ]) + "\n"
        proc = subprocess.run([sys.executable, str(SERVER)], input=requests, text=True, capture_output=True, check=True)
        lines = [json.loads(line) for line in proc.stdout.splitlines()]
        self.assertEqual(len(lines), 3)
        for line in lines:
            with self.subTest(line=line):
                assert_response_envelope(self, line)
                self.assertFalse(line["ok"])
                self.assertEqual(line["error"]["code"], "invalid_json")
                self.assertIn("invalid JSON constant", " ".join(line["error"]["details"]["errors"]))
                self.assertIn("tool-request.schema.json", line["error"]["details"]["schema"])

    def test_response_schema_has_only_documented_flexible_pockets(self):
        schema = json.loads((ROOT / "schemas" / "tool-response.schema.json").read_text(encoding="utf-8"))
        allowed = {
            "$defs.capabilities_result.properties.examples.items.properties.params.additionalProperties",
            "$defs.export_result.properties.card.additionalProperties",
            "$defs.audit_event.properties.data.additionalProperties",
            "$defs.source_result.properties.metadata.additionalProperties",
        }
        found = set()

        def walk(value, path):
            if isinstance(value, dict):
                if value.get("additionalProperties") is True:
                    found.add(".".join(path + ["additionalProperties"]))
                for key, child in value.items():
                    walk(child, path + [key])
            elif isinstance(value, list):
                for index, child in enumerate(value):
                    walk(child, path + [str(index)])

        walk(schema, [])
        self.assertEqual(found, allowed)

    def test_response_schema_documents_write_review_shapes(self):
        schema = json.loads((ROOT / "schemas" / "tool-response.schema.json").read_text(encoding="utf-8"))
        defs = schema["$defs"]
        approval = defs["approval_required_details"]
        dry_run = defs["dry_run_review_result"]
        ingest_dry_run = defs["ingest_dry_run_result"]
        self.assertEqual(approval["properties"]["dry_run"], {"const": False})
        self.assertEqual(approval["properties"]["review_required"], {"const": True})
        self.assertIn("apply_instruction", approval["required"])
        self.assertFalse(dry_run["additionalProperties"])
        self.assertEqual(dry_run["properties"]["dry_run"], {"const": True})
        self.assertEqual(dry_run["properties"]["review_required"], {"const": True})
        self.assertEqual(dry_run["properties"]["would_write"], {"const": True})
        for field in ["method", "path", "argv", "redacted", "apply_instruction"]:
            self.assertIn(field, dry_run["required"])
        ingest_apply = defs["ingest_result"]
        crystallize = defs["crystallize_session_result"]
        session_start = defs["session_start_result"]
        session_preview = defs["session_end_preview_result"]
        self.assertFalse(ingest_dry_run["additionalProperties"])
        for field in ["source_id", "page", "signals", "created_claims", "redacted", "would_write"]:
            self.assertIn(field, ingest_dry_run["required"])
        self.assertFalse(ingest_apply["additionalProperties"])
        for field in ["ok", "source_id", "page", "signals", "created_claims", "redacted"]:
            self.assertIn(field, ingest_apply["required"])
        self.assertFalse(crystallize["additionalProperties"])
        self.assertFalse(crystallize["properties"]["summary"]["additionalProperties"])
        for field in ["session_id", "summary", "page", "source_id", "created_claims", "skipped_claims"]:
            self.assertIn(field, crystallize["required"])
        self.assertFalse(session_start["additionalProperties"])
        for field in ["session_id", "task", "context"]:
            self.assertIn(field, session_start["required"])
        self.assertFalse(session_preview["additionalProperties"])
        for field in ["session_id", "summary", "page", "dry_run", "would_write", "review_required", "apply_instruction"]:
            self.assertIn(field, session_preview["required"])
        capabilities = defs["capabilities_result"]
        self.assertFalse(capabilities["additionalProperties"])
        self.assertFalse(capabilities["properties"]["features"]["additionalProperties"])
        self.assertIn("unknown_request_field_rejection", capabilities["properties"]["features"]["required"])
        self.assertIn("param_array_validation", capabilities["properties"]["features"]["required"])
        self.assertIn("param_enum_validation", capabilities["properties"]["features"]["required"])
        self.assertIn("param_numeric_range_validation", capabilities["properties"]["features"]["required"])
        self.assertIn("param_min_length_validation", capabilities["properties"]["features"]["required"])
        self.assertIn("cli_error_redaction", capabilities["properties"]["features"]["required"])
        self.assertIn("strict_json_parse", capabilities["properties"]["features"]["required"])
        self.assertIn("strict_json_output", capabilities["properties"]["features"]["required"])
        self.assertIn("finite_request_id_validation", capabilities["properties"]["features"]["required"])
        self.assertIn("request_id_string_validation", capabilities["properties"]["features"]["required"])
        self.assertIn("finite_numeric_param_validation", capabilities["properties"]["features"]["required"])
        self.assertIn("method_schema_runtime_parity", capabilities["properties"]["features"]["required"])
        self.assertIn("bounded_context", capabilities["properties"]["features"]["required"])
        self.assertIn("session_lifecycle_entrypoints", capabilities["properties"]["features"]["required"])
        self.assertIn("cli_error_output_truncation", capabilities["properties"]["features"]["required"])
        self.assertIn("request_id_numeric_bounds", capabilities["properties"]["features"]["required"])
        self.assertIn("capability_negotiation", capabilities["properties"]["features"]["required"])
        self.assertIn("negotiation", capabilities["required"])
        self.assertIn("knowledge_capability", capabilities["required"])
        self.assertIn("profiles", capabilities["required"])
        self.assertIn("profile_contracts", capabilities["required"])
        knowledge_capability = capabilities["properties"]["knowledge_capability"]
        self.assertFalse(knowledge_capability["additionalProperties"])
        for field in ["kind", "artifact_model", "transport", "scope", "trust_model", "retrieval", "writes", "portability"]:
            self.assertIn(field, knowledge_capability["required"])
        self.assertEqual(knowledge_capability["properties"]["kind"], {"const": "agent_knowledge_base"})
        self.assertEqual(knowledge_capability["properties"]["trust_model"], {"const": "cited_review_gated_memory"})
        self.assertFalse(knowledge_capability["properties"]["retrieval"]["additionalProperties"])
        self.assertFalse(knowledge_capability["properties"]["writes"]["additionalProperties"])
        self.assertFalse(knowledge_capability["properties"]["portability"]["additionalProperties"])
        negotiation = capabilities["properties"]["negotiation"]
        self.assertFalse(negotiation["additionalProperties"])
        self.assertIn("requested_features", negotiation["required"])
        self.assertIn("unsupported_features", negotiation["required"])
        self.assertIn("requested_profiles", negotiation["required"])
        self.assertIn("unsupported_profiles", negotiation["required"])
        self.assertIn("requested_methods", negotiation["required"])
        self.assertIn("unsupported_methods", negotiation["required"])
        self.assertIn("satisfied", negotiation["required"])
        self.assertIn("max_request_id_length", capabilities["properties"]["runtime"]["required"])
        self.assertIn("max_request_id_abs_value", capabilities["properties"]["runtime"]["required"])
        self.assertIn("max_error_output_bytes", capabilities["properties"]["runtime"]["required"])
        self.assertIn("request_id_policy", capabilities["properties"]["runtime"]["required"])
        self.assertIn("cli_error_output_policy", capabilities["properties"]["runtime"]["required"])
        self.assertIn("param_array_policy", capabilities["properties"]["runtime"]["required"])
        self.assertIn("param_enum_policy", capabilities["properties"]["runtime"]["required"])
        self.assertIn("param_numeric_range_policy", capabilities["properties"]["runtime"]["required"])
        self.assertIn("context_budget_policy", capabilities["properties"]["runtime"]["required"])
        self.assertIn("param_min_length_policy", capabilities["properties"]["runtime"]["required"])
        self.assertIn("finite_numeric_param_policy", capabilities["properties"]["runtime"]["required"])
        self.assertIn("method_schema_parity_policy", capabilities["properties"]["runtime"]["required"])
        self.assertIn("method_schema_runtime_errors", capabilities["properties"]["runtime"]["required"])
        self.assertFalse(capabilities["properties"]["methods"]["additionalProperties"]["additionalProperties"])
        self.assertFalse(capabilities["properties"]["profiles"]["additionalProperties"])
        self.assertFalse(capabilities["properties"]["profile_contracts"]["additionalProperties"])
        for profile in ["read_only", "startup_context", "reviewed_write", "lifecycle", "portability", "maintenance"]:
            self.assertIn(profile, capabilities["properties"]["profiles"]["required"])
            self.assertIn(profile, capabilities["properties"]["profile_contracts"]["required"])
        self.assertFalse(capabilities["properties"]["examples"]["items"]["additionalProperties"])
        self.assertIn("features", capabilities["required"])
        self.assertIn("methods", capabilities["required"])
        self.assertEqual(capabilities["properties"]["protocol"], {"const": "akbp-jsonl-tool-server"})
        self.assertFalse(defs["context_result"]["additionalProperties"])
        self.assertIn("items", defs["context_result"]["required"])
        self.assertIn("warnings", defs["context_result"]["required"])
        self.assertIn("quality", defs["context_result"]["required"])
        self.assertIn("quality", defs["context_result"]["properties"])
        self.assertFalse(defs["context_result"]["properties"]["quality"]["additionalProperties"])
        self.assertIn("ok", defs["context_result"]["properties"]["quality"]["required"])
        self.assertFalse(defs["search_result"]["additionalProperties"])
        self.assertIn("backend", defs["search_result"]["required"])
        self.assertIn("results", defs["search_result"]["required"])
        self.assertIn("warnings", defs["search_result"]["required"])
        self.assertFalse(defs["status_result"]["additionalProperties"])
        self.assertIn("initialized", defs["status_result"]["required"])
        self.assertIn("entrypoint", defs["status_result"]["required"])
        self.assertFalse(defs["doctor_result"]["additionalProperties"])
        self.assertIn("ready_for_adapter", defs["doctor_result"]["required"])
        self.assertIn("next_steps", defs["doctor_result"]["required"])
        self.assertFalse(defs["index_result"]["additionalProperties"])
        self.assertIn("indexed", defs["index_result"]["required"])
        self.assertIn("incremental", defs["index_result"]["required"])
        self.assertIn("indexed_keys", defs["index_result"]["required"])
        self.assertIn("skipped_keys", defs["index_result"]["required"])
        self.assertIn("removed_keys", defs["index_result"]["required"])
        self.assertFalse(defs["cite_result"]["additionalProperties"])
        self.assertIn("claim_id", defs["cite_result"]["required"])
        self.assertFalse(defs["audit_result"]["additionalProperties"])
        self.assertIn("events", defs["audit_result"]["required"])
        self.assertFalse(defs["export_result"]["additionalProperties"])
        self.assertIn("claims", defs["export_result"]["required"])
        self.assertFalse(defs["context_item"]["additionalProperties"])
        self.assertIn("summary", defs["context_item"]["required"])
        self.assertFalse(defs["search_result_row"]["additionalProperties"])
        self.assertIn("snippet", defs["search_result_row"]["required"])
        for name in ["audit_event", "exported_claim", "claim_result", "source_result", "entity_result", "relation_result"]:
            self.assertFalse(defs[name]["additionalProperties"])
        self.assertIn("event", defs["audit_event"]["required"])
        self.assertIn("operation", defs["audit_event"]["required"])
        self.assertIn("confidence", defs["exported_claim"]["required"])
        self.assertIn("superseded_by", defs["exported_claim"]["properties"])
        self.assertIn("text", defs["claim_result"]["required"])
        self.assertIn("last_confirmed_at", defs["claim_result"]["properties"])
        self.assertIn("locator", defs["source_result"]["required"])
        self.assertIn("name", defs["entity_result"]["required"])
        self.assertIn("relation", defs["relation_result"]["required"])
        invalid_request = defs["invalid_request_details"]
        invalid_json = defs["invalid_json_details"]
        invalid_params = defs["invalid_params_details"]
        cli_error = defs["cli_error_details"]
        internal_error = defs["internal_error_details"]
        unknown_method = defs["unknown_method_details"]
        self.assertIn("method", cli_error["required"])
        self.assertIn("exit_code", cli_error["required"])
        self.assertIn("stdout", cli_error["required"])
        self.assertIn("redacted", cli_error["required"])
        self.assertIn("truncated", cli_error["required"])
        self.assertIn("errors", internal_error["required"])
        for details_schema in [
            approval,
            cli_error,
            internal_error,
            invalid_request,
            invalid_json,
            invalid_params,
            unknown_method,
        ]:
            self.assertFalse(details_schema["additionalProperties"])
        self.assertIn("errors", invalid_request["required"])
        self.assertIn("schema", invalid_request["required"])
        self.assertIn("errors", invalid_json["required"])
        self.assertIn("schema", invalid_json["required"])
        self.assertIn("params_schema", invalid_params["required"])
        self.assertIn("available_methods", unknown_method["required"])
        details = schema["properties"]["error"]["anyOf"][1]["properties"]["details"]
        for ref in [
            "#/$defs/approval_required_details",
            "#/$defs/invalid_request_details",
            "#/$defs/invalid_json_details",
            "#/$defs/cli_error_details",
            "#/$defs/internal_error_details",
            "#/$defs/invalid_params_details",
            "#/$defs/unknown_method_details",
        ]:
            self.assertIn({"$ref": ref}, details["anyOf"])

    def test_capabilities_method_schema_refs_match_schema_defs(self):
        method_schema = json.loads((ROOT / "schemas" / "tool-methods.schema.json").read_text(encoding="utf-8"))
        defs = method_schema["$defs"]
        proc = subprocess.run(
            [sys.executable, str(SERVER)],
            input=json.dumps({"id": "caps", "method": "akbp.capabilities"}) + "\n",
            text=True,
            capture_output=True,
            check=True,
        )
        line = json.loads(proc.stdout)
        self.assertTrue(line["ok"])
        assert_matches_required_schema(self, line["result"], schema_def("capabilities_result"))
        methods = line["result"]["methods"]
        self.assertGreaterEqual(len(methods), 10)
        for method, meta in methods.items():
            with self.subTest(method=method):
                ref = meta.get("params_schema")
                self.assertIsNotNone(ref)
                self.assertTrue(ref.startswith(line["result"]["schemas"]["methods"] + "#/$defs/"))
                def_name = ref.rsplit("/", 1)[-1]
                self.assertIn(def_name, defs)
                self.assertEqual(bool(meta["write"]), bool(meta["review_required"]))
                params = set(meta["params"])
                schema_params = set(defs[def_name].get("properties", {}))
                self.assertEqual(params, schema_params, method)

    def test_method_schemas_match_runtime_required_params(self):
        method_schema = json.loads((ROOT / "schemas" / "tool-methods.schema.json").read_text(encoding="utf-8"))
        defs = method_schema["$defs"]
        server = load_server_module()
        for method, required in server.REQUIRED_PARAMS.items():
            with self.subTest(method=method):
                schema_required = tuple(defs[f"{method}.params"].get("required", []))
                self.assertEqual(schema_required, tuple(required))

    def test_server_runtime_schema_parity_check_is_clean(self):
        server = load_server_module()
        self.assertEqual(server.SCHEMA_RUNTIME_ERRORS, [])
        self.assertEqual(server.method_schema_runtime_errors(), [])

    def test_method_schemas_match_runtime_control_char_params(self):
        method_schema = json.loads((ROOT / "schemas" / "tool-methods.schema.json").read_text(encoding="utf-8"))
        defs = method_schema["$defs"]
        server = load_server_module()
        expected_pattern = "^[^\\u0000\\n\\r]*$"
        documented = set()
        for def_name, definition in defs.items():
            if not def_name.startswith("akbp."):
                continue
            for param_name, spec in definition.get("properties", {}).items():
                if param_name in server.CONTROL_CHAR_STRING_PARAMS:
                    with self.subTest(definition=def_name, param=param_name):
                        self.assertEqual(spec.get("pattern"), expected_pattern)
                        documented.add(param_name)
        self.assertEqual(documented, server.CONTROL_CHAR_STRING_PARAMS)

    def test_installed_server_capabilities_match_reference_server(self):
        request = json.dumps({"id": "caps", "method": "akbp.capabilities"}) + "\n"
        reference = subprocess.run([sys.executable, str(SERVER)], input=request, text=True, capture_output=True, check=True)
        installed = subprocess.run([sys.executable, str(INSTALLED_SERVER)], input=request, text=True, capture_output=True, check=True)
        reference_result = json.loads(reference.stdout)["result"]
        installed_result = json.loads(installed.stdout)["result"]
        self.assertEqual(installed_result["features"], reference_result["features"])
        self.assertEqual(installed_result["runtime"], reference_result["runtime"])
        self.assertEqual(installed_result["knowledge_capability"], reference_result["knowledge_capability"])
        self.assertEqual(set(installed_result["methods"]), set(reference_result["methods"]))
        self.assertEqual(installed_result["knowledge_capability"]["kind"], "agent_knowledge_base")
        self.assertEqual(installed_result["knowledge_capability"]["trust_model"], "cited_review_gated_memory")
        self.assertEqual(installed_result["knowledge_capability"]["retrieval"]["startup_method"], "akbp.session.start")
        self.assertIn("akbp.doctor", installed_result["methods"])
        self.assertIn("akbp.import_apply", installed_result["methods"])
        self.assertIn("akbp.session.start", installed_result["methods"])
        self.assertIn("akbp.session.end", installed_result["methods"])
        self.assertTrue(installed_result["features"]["method_param_schemas"])
        self.assertTrue(installed_result["features"]["approval_required_errors"])
        self.assertTrue(installed_result["features"]["max_request_bytes_enforced"])
        self.assertTrue(installed_result["features"]["path_validation"])
        self.assertTrue(installed_result["features"]["dry_run_argv_redaction"])
        self.assertTrue(installed_result["features"]["param_enum_validation"])
        self.assertTrue(installed_result["features"]["param_numeric_range_validation"])
        self.assertTrue(installed_result["features"]["param_min_length_validation"])
        self.assertTrue(installed_result["features"]["strict_json_parse"])
        self.assertTrue(installed_result["features"]["method_schema_runtime_parity"])
        self.assertTrue(installed_result["features"]["bounded_context"])
        self.assertTrue(installed_result["features"]["session_lifecycle_entrypoints"])
        self.assertTrue(installed_result["features"]["request_id_numeric_bounds"])
        self.assertTrue(installed_result["features"]["cli_error_output_truncation"])
        self.assertEqual(installed_result["runtime"]["max_request_id_abs_value"], reference_result["runtime"]["max_request_id_abs_value"])
        self.assertEqual(installed_result["runtime"]["path_policy"], reference_result["runtime"]["path_policy"])
        self.assertEqual(installed_result["runtime"]["method_schema_parity_policy"], reference_result["runtime"]["method_schema_parity_policy"])

    def test_cli_error_response_truncates_large_output_after_redaction(self):
        server = load_server_module()
        oversized = "x" * (server.MAX_ERROR_OUTPUT_BYTES + 100)
        response = server.cli_error_response("err", "akbp.status", 2, oversized, oversized)
        assert_response_envelope(self, response)
        self.assertFalse(response["ok"])
        details = response["error"]["details"]
        self.assertEqual(details["method"], "akbp.status")
        self.assertTrue(details["truncated"])
        self.assertFalse(details["redacted"])
        self.assertLess(len(details["stdout"]), len(oversized))
        self.assertTrue(details["stdout"].endswith("[truncated]"))
        self.assertTrue(response["error"]["message"].endswith("[truncated]"))

    def test_status_context_and_capabilities_methods(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            run_cli("--path", str(kb), "init")
            run_cli("--path", str(kb), "remember", "AKBP keeps durable claims", "--evidence", "AKBP.md")
            requests = "\n".join([
                json.dumps({"id": "caps", "path": str(kb), "method": "akbp.capabilities"}),
                json.dumps({"id": "1", "path": str(kb), "method": "akbp.status"}),
                json.dumps({"id": "doctor", "path": str(kb), "method": "akbp.doctor"}),
                json.dumps({"id": "2", "path": str(kb), "method": "akbp.context", "params": {"task": "durable claims", "max_chars": 24, "min_items": 1, "require_citations": True}}),
            ]) + "\n"
            proc = subprocess.run([sys.executable, str(SERVER)], input=requests, text=True, capture_output=True, check=True)
            lines = [json.loads(line) for line in proc.stdout.splitlines()]
            self.assertEqual(lines[0]["id"], "caps")
            self.assertTrue(lines[0]["result"]["features"]["capability_discovery"])
            self.assertTrue(lines[0]["result"]["features"]["write_review_required"])
            self.assertTrue(lines[0]["result"]["features"]["write_apply_requires_approval"])
            self.assertTrue(lines[0]["result"]["features"]["method_param_schemas"])
            self.assertTrue(lines[0]["result"]["features"]["max_request_bytes_enforced"])
            self.assertTrue(lines[0]["result"]["features"]["path_validation"])
            self.assertTrue(lines[0]["result"]["features"]["dry_run_argv_redaction"])
            self.assertIn("path_policy", lines[0]["result"]["runtime"])
            self.assertTrue(lines[0]["result"]["features"]["unknown_param_rejection"])
            self.assertTrue(lines[0]["result"]["features"]["required_param_validation"])
            self.assertTrue(lines[0]["result"]["features"]["param_array_validation"])
            self.assertTrue(lines[0]["result"]["features"]["param_min_length_validation"])
            self.assertTrue(lines[0]["result"]["features"]["param_enum_validation"])
            self.assertTrue(lines[0]["result"]["features"]["param_numeric_range_validation"])
            self.assertTrue(lines[0]["result"]["features"]["strict_json_parse"])
            self.assertTrue(lines[0]["result"]["features"]["method_schema_runtime_parity"])
            self.assertTrue(lines[0]["result"]["features"]["bounded_context"])
            self.assertTrue(lines[0]["result"]["features"]["session_lifecycle_entrypoints"])
            self.assertEqual(lines[0]["result"]["runtime"]["method_schema_runtime_errors"], [])
            self.assertTrue(lines[0]["result"]["features"]["request_id_numeric_bounds"])
            self.assertTrue(lines[0]["result"]["features"]["capability_negotiation"])
            self.assertEqual(lines[0]["result"]["negotiation"]["requested_features"], [])
            self.assertEqual(lines[0]["result"]["negotiation"]["supported_features"], [])
            self.assertEqual(lines[0]["result"]["negotiation"]["unsupported_features"], [])
            self.assertEqual(lines[0]["result"]["negotiation"]["requested_methods"], [])
            self.assertEqual(lines[0]["result"]["negotiation"]["supported_methods"], [])
            self.assertEqual(lines[0]["result"]["negotiation"]["unsupported_methods"], [])
            self.assertTrue(lines[0]["result"]["negotiation"]["satisfied"])
            self.assertEqual(lines[0]["result"]["runtime"]["max_request_id_abs_value"], 9007199254740991)
            self.assertIn("safe integer range", lines[0]["result"]["runtime"]["request_id_policy"])
            self.assertIn("arrays are capped", lines[0]["result"]["runtime"]["param_array_policy"])
            self.assertIn("enum params", lines[0]["result"]["runtime"]["param_enum_policy"])
            self.assertIn("schema bounds", lines[0]["result"]["runtime"]["param_numeric_range_policy"])
            self.assertIn("non-finite floats", lines[0]["result"]["runtime"]["finite_numeric_param_policy"])
            self.assertIn("non-empty string params", lines[0]["result"]["runtime"]["param_min_length_policy"])
            self.assertTrue(lines[0]["result"]["features"]["approval_required_errors"])
            self.assertEqual(lines[0]["result"]["runtime"]["transport"], "jsonl-stdio")
            self.assertEqual(lines[0]["result"]["runtime"]["write_policy"], "review-gated")
            self.assertEqual(lines[0]["result"]["knowledge_capability"]["kind"], "agent_knowledge_base")
            self.assertEqual(lines[0]["result"]["knowledge_capability"]["trust_model"], "cited_review_gated_memory")
            self.assertEqual(lines[0]["result"]["knowledge_capability"]["retrieval"]["startup_method"], "akbp.session.start")
            self.assertEqual(lines[0]["result"]["knowledge_capability"]["writes"]["policy"], "dry_run_preview_then_approved_apply")
            self.assertEqual(lines[0]["result"]["knowledge_capability"]["writes"]["approval_required_error"], "approval_required")
            self.assertIn("sha256", lines[0]["result"]["runtime"]["hash_algorithms"])
            self.assertEqual(lines[0]["result"]["schemas"]["request"].split("/")[-1], "tool-request.schema.json")
            self.assertEqual(lines[0]["result"]["schemas"]["response"].split("/")[-1], "tool-response.schema.json")
            self.assertIn("akbp.remember", lines[0]["result"]["methods"])
            self.assertIn("akbp.doctor", lines[0]["result"]["methods"])
            self.assertIn("akbp.ingest", lines[0]["result"]["methods"])
            self.assertIn("akbp.import_check", lines[0]["result"]["methods"])
            self.assertIn("akbp.import_apply", lines[0]["result"]["methods"])
            self.assertIn("akbp.index", lines[0]["result"]["methods"])
            self.assertIn("akbp.search", lines[0]["result"]["methods"])
            self.assertIn("akbp.audit", lines[0]["result"]["methods"])
            profiles = lines[0]["result"]["profiles"]
            self.assertIn("akbp.search", profiles["read_only"])
            self.assertIn("akbp.import_check", profiles["read_only"])
            self.assertIn("akbp.session.start", profiles["startup_context"])
            self.assertIn("akbp.remember", profiles["reviewed_write"])
            self.assertIn("akbp.supersede", profiles["lifecycle"])
            self.assertIn("akbp.export_check", profiles["portability"])
            self.assertIn("akbp.source.verify", profiles["maintenance"])
            for group in profiles.values():
                for method in group:
                    self.assertIn(method, lines[0]["result"]["methods"])
            for method in profiles["read_only"]:
                self.assertFalse(lines[0]["result"]["methods"][method]["write"], method)
            self.assertTrue(lines[0]["result"]["methods"]["akbp.remember"]["review_required"])
            self.assertFalse(lines[0]["result"]["methods"]["akbp.query"]["review_required"])
            examples = lines[0]["result"]["examples"]
            crystallize_examples = [item for item in examples if item["method"] == "akbp.crystallize_session"]
            self.assertTrue(crystallize_examples)
            self.assertTrue(crystallize_examples[0]["dry_run"])
            self.assertTrue(crystallize_examples[0]["params"]["apply"])
            for method in ["akbp.status", "akbp.doctor", "akbp.remember", "akbp.ingest", "akbp.import_check", "akbp.import_apply", "akbp.index", "akbp.search", "akbp.audit", "akbp.cite", "akbp.crystallize_session"]:
                self.assertTrue(lines[0]["result"]["methods"][method]["params_schema"].endswith(f"#/$defs/{method}.params"))
            self.assertEqual(lines[1]["id"], "1")
            self.assertTrue(lines[1]["ok"])
            assert_matches_required_schema(self, lines[1]["result"], schema_def("status_result"))
            self.assertEqual(lines[2]["id"], "doctor")
            self.assertTrue(lines[2]["ok"])
            assert_matches_required_schema(self, lines[2]["result"], schema_def("doctor_result"))
            self.assertTrue(lines[2]["result"]["ok"])
            self.assertEqual(lines[2]["result"]["summary"]["errors"], 0)
            self.assertEqual(lines[2]["result"]["workflow"]["total"], 6)
            self.assertEqual(lines[2]["result"]["workflow"]["current_stage"], "register_evidence")
            self.assertEqual(lines[3]["id"], "2")
            assert_matches_required_schema(self, lines[3]["result"], schema_def("context_result"))
            self.assertTrue(lines[3]["ok"])
            self.assertTrue(lines[3]["result"]["items"])
            self.assertTrue(lines[3]["result"]["quality"]["ok"])
            self.assertEqual(lines[3]["result"]["quality"]["minimum_items"], 1)
            self.assertTrue(lines[3]["result"]["quality"]["require_citations"])
            self.assertLessEqual(lines[3]["result"]["budget"]["summary_chars"], 24)
            self.assertEqual(
                lines[3]["result"]["budget"]["truncated_items"],
                lines[3]["result"]["budget"]["clipped_items"] + lines[3]["result"]["budget"]["omitted_items"],
            )
            self.assertGreaterEqual(lines[3]["result"]["budget"]["items_before_budget"], lines[3]["result"]["budget"]["items_after_budget"])
            self.assertEqual(lines[3]["result"]["budget"]["items_after_budget"], len(lines[3]["result"]["items"]))
            assert_matches_required_schema(self, lines[3]["result"]["items"][0], schema_def("context_item"))

    def test_capabilities_negotiates_required_features(self):
        request = json.dumps({
            "id": "caps-negotiate",
            "method": "akbp.capabilities",
            "params": {
                "client": "adapter-test",
                "requires": ["method_param_schemas", "features.capability_negotiation", "future_feature"],
                "requires_methods": ["akbp.session.start", "akbp.remember", "akbp.future"],
            },
        }) + "\n"
        proc = subprocess.run([sys.executable, str(SERVER)], input=request, text=True, capture_output=True, check=True)
        line = json.loads(proc.stdout)
        assert_response_envelope(self, line)
        assert_matches_required_schema(self, line["result"], schema_def("capabilities_result"))
        negotiation = line["result"]["negotiation"]
        self.assertEqual(negotiation["client"], "adapter-test")
        self.assertEqual(negotiation["requested_features"], ["method_param_schemas", "features.capability_negotiation", "future_feature"])
        self.assertEqual(negotiation["supported_features"], ["method_param_schemas", "features.capability_negotiation"])
        self.assertEqual(negotiation["unsupported_features"], ["future_feature"])
        self.assertEqual(negotiation["requested_methods"], ["akbp.session.start", "akbp.remember", "akbp.future"])
        self.assertEqual(negotiation["supported_methods"], ["akbp.session.start", "akbp.remember"])
        self.assertEqual(negotiation["unsupported_methods"], ["akbp.future"])
        self.assertFalse(negotiation["satisfied"])

    def test_capabilities_negotiation_params_are_bounded(self):
        requests = "\n".join([
            json.dumps({"id": "bad-client", "method": "akbp.capabilities", "params": {"client": "x" * 129}}),
            json.dumps({"id": "bad-requires", "method": "akbp.capabilities", "params": {"requires": [""]}}),
            json.dumps({"id": "bad-methods", "method": "akbp.capabilities", "params": {"requires_methods": [""]}}),
        ]) + "\n"
        proc = subprocess.run([sys.executable, str(SERVER)], input=requests, text=True, capture_output=True, check=True)
        lines = [json.loads(line) for line in proc.stdout.splitlines()]
        self.assertEqual(len(lines), 3)
        for line in lines:
            with self.subTest(line=line):
                assert_response_envelope(self, line)
                self.assertFalse(line["ok"])
                self.assertEqual(line["error"]["code"], "invalid_params")
                self.assertTrue(line["error"]["details"]["params_schema"].endswith("#/$defs/akbp.capabilities.params"))

    def test_generic_dry_run_redacts_secret_like_argv(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            run_cli("--path", str(kb), "init")
            secret = "token=ghp_abcdefghijklmnopqrstuvwxyz123456"
            request = json.dumps({"id": "dry", "path": str(kb), "method": "akbp.remember", "dry_run": True, "params": {"text": f"Rotate {secret}"}}) + "\n"
            proc = subprocess.run([sys.executable, str(SERVER)], input=request, text=True, capture_output=True, check=True)
            line = json.loads(proc.stdout)
            self.assertTrue(line["ok"])
            self.assertTrue(line["result"]["redacted"])
            self.assertNotIn(secret, json.dumps(line))
            self.assertIn("[REDACTED]", json.dumps(line))
            claims = kb / "claims" / "claims.jsonl"
            self.assertNotIn(secret, claims.read_text(encoding="utf-8") if claims.exists() else "")

    def test_write_methods_and_dry_run(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            run_cli("--path", str(kb), "init")
            requests = "\n".join([
                json.dumps({"id": "dry", "path": str(kb), "method": "akbp.remember", "dry_run": True, "params": {"text": "AKBP dry run does not write"}}),
                json.dumps({"id": "param-dry", "path": str(kb), "method": "akbp.source.add", "params": {"locator": "AKBP.md", "dry_run": True}}),
                json.dumps({"id": "unapproved", "path": str(kb), "method": "akbp.remember", "params": {"text": "AKBP should reject unapproved non-dry-run writes"}}),
                json.dumps({"id": "source", "path": str(kb), "method": "akbp.source.add", "approved": True, "params": {"locator": "AKBP.md", "type": "file", "title": "Entry point"}}),
                json.dumps({"id": "remember", "path": str(kb), "method": "akbp.remember", "approved": True, "params": {"text": "AKBP has a JSONL local tool server", "type": "fact", "evidence": ["AKBP.md"]}}),
            ]) + "\n"
            proc = subprocess.run([sys.executable, str(SERVER)], input=requests, text=True, capture_output=True, check=True)
            lines = [json.loads(line) for line in proc.stdout.splitlines()]
            self.assertTrue(lines[0]["ok"])
            self.assertTrue(lines[1]["ok"])
            self.assertFalse(lines[2]["ok"])
            self.assertEqual(lines[2]["error"]["code"], "approval_required")
            self.assertIn("approved:true", lines[2]["error"]["message"])
            self.assertTrue(lines[3]["ok"])
            self.assertTrue(lines[4]["ok"])
            self.assertTrue(lines[0]["result"]["dry_run"])
            self.assertTrue(lines[0]["result"]["review_required"])
            self.assertIn("approval", lines[0]["result"]["apply_instruction"])
            self.assertTrue(lines[1]["result"]["dry_run"])
            self.assertTrue(lines[1]["result"]["review_required"])
            self.assertEqual(lines[1]["result"]["method"], "akbp.source.add")
            self.assertEqual(lines[3]["result"]["type"], "file")
            self.assertEqual(lines[4]["result"]["type"], "fact")
            claims = (kb / "claims" / "claims.jsonl").read_text()
            self.assertNotIn("AKBP dry run does not write", claims)

    def test_all_write_methods_enforce_approval_boundary(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            transcript = Path(d) / "session.md"
            transcript.write_text("# Session\n\nDecision: review before apply.\n", encoding="utf-8")
            note = Path(d) / "note.md"
            note.write_text("# Note\n\nDecision: import safely.\n", encoding="utf-8")
            examples = {
                "akbp.remember": {"text": "Adapters dry-run before durable writes"},
                "akbp.source.add": {"locator": "AKBP.md"},
                "akbp.ingest": {"file": str(note), "claim": "Imports start with review."},
                "akbp.index": {"incremental": True},
                "akbp.supersede": {"old_claim_id": "claim_old", "text": "Newer claim requires review."},
                "akbp.contradict": {"source_claim_id": "claim_a", "target_claim_id": "claim_b"},
                "akbp.crystallize_session": {"transcript": str(transcript), "apply": True},
            }
            requests = []
            for method, params in examples.items():
                requests.append(json.dumps({"id": f"dry-{method}", "path": str(kb), "method": method, "dry_run": True, "params": params}))
                requests.append(json.dumps({"id": f"reject-{method}", "path": str(kb), "method": method, "params": params}))
            proc = subprocess.run([sys.executable, str(SERVER)], input="\n".join(requests) + "\n", text=True, capture_output=True, check=True)
            lines = [json.loads(line) for line in proc.stdout.splitlines()]
            self.assertEqual(len(lines), len(requests))
            dry_run_schema = schema_def("dry_run_review_result")
            ingest_dry_run_schema = schema_def("ingest_dry_run_result")
            session_preview_schema = schema_def("session_end_preview_result")
            approval_schema = schema_def("approval_required_details")
            for dry, rejected in zip(lines[0::2], lines[1::2]):
                with self.subTest(request=dry["id"]):
                    self.assertTrue(dry["ok"])
                    if dry["id"] == "dry-akbp.ingest":
                        expected_schema = ingest_dry_run_schema
                    elif dry["id"] == "dry-akbp.crystallize_session":
                        expected_schema = session_preview_schema
                    else:
                        expected_schema = dry_run_schema
                    assert_matches_required_schema(self, dry["result"], expected_schema)
                    self.assertTrue(dry["result"]["dry_run"])
                    self.assertTrue(dry["result"]["review_required"])
                    self.assertIn("approval", dry["result"]["apply_instruction"])
                with self.subTest(request=rejected["id"]):
                    self.assertFalse(rejected["ok"])
                    self.assertEqual(rejected["error"]["code"], "approval_required")
                    assert_matches_required_schema(self, rejected["error"]["details"], approval_schema)
                    self.assertTrue(rejected["error"]["details"]["review_required"])
                    self.assertIn("approved:true", rejected["error"]["message"])
                    self.assertIn("approved:true", rejected["error"]["details"]["apply_instruction"])

    def test_index_and_search_methods(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            run_cli("--path", str(kb), "init")
            run_cli("--path", str(kb), "remember", "SQLite index supports tool server search", "--evidence", "AKBP.md")
            requests = "\n".join([
                json.dumps({"id": "index", "path": str(kb), "method": "akbp.index", "approved": True, "params": {"incremental": True}}),
                json.dumps({"id": "search", "path": str(kb), "method": "akbp.search", "params": {"query": "SQLite: search", "limit": 5}}),
            ]) + "\n"
            proc = subprocess.run([sys.executable, str(SERVER)], input=requests, text=True, capture_output=True, check=True)
            lines = [json.loads(line) for line in proc.stdout.splitlines()]
            self.assertTrue(lines[0]["ok"])
            assert_matches_required_schema(self, lines[0]["result"], schema_def("index_result"))
            self.assertTrue(lines[0]["result"]["incremental"])
            self.assertIn("indexed_keys", lines[0]["result"])
            self.assertIn("skipped_keys", lines[0]["result"])
            self.assertIn("removed_keys", lines[0]["result"])
            self.assertTrue(lines[1]["ok"])
            assert_matches_required_schema(self, lines[1]["result"], schema_def("search_result"))
            self.assertEqual(lines[1]["result"]["backend"], "sqlite_fts5")
            self.assertTrue(lines[1]["result"]["results"])
            assert_matches_required_schema(self, lines[1]["result"]["results"][0], schema_def("search_result_row"))



    def test_write_apply_response_shapes(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            run_cli("--path", str(kb), "init")
            old = json.loads(run_cli("--path", str(kb), "remember", "Old claim", "--evidence", "old.md").stdout)["id"]
            claim_a = json.loads(run_cli("--path", str(kb), "remember", "A claim", "--evidence", "a.md").stdout)["id"]
            claim_b = json.loads(run_cli("--path", str(kb), "remember", "B claim", "--evidence", "b.md").stdout)["id"]
            requests = "\n".join([
                json.dumps({"id": "remember", "path": str(kb), "method": "akbp.remember", "approved": True, "params": {"text": "Remember result shape", "type": "fact", "evidence": ["doc.md"]}}),
                json.dumps({"id": "source", "path": str(kb), "method": "akbp.source.add", "approved": True, "params": {"locator": "doc.md", "type": "file", "title": "Doc"}}),
                json.dumps({"id": "supersede", "path": str(kb), "method": "akbp.supersede", "approved": True, "params": {"old_claim_id": old, "text": "New claim", "type": "decision", "evidence": ["new.md"]}}),
                json.dumps({"id": "contradict", "path": str(kb), "method": "akbp.contradict", "approved": True, "params": {"source_claim_id": claim_a, "target_claim_id": claim_b, "evidence": ["review.md"]}}),
            ]) + "\n"
            proc = subprocess.run([sys.executable, str(SERVER)], input=requests, text=True, capture_output=True, check=True)
            lines = [json.loads(line) for line in proc.stdout.splitlines()]
            self.assertEqual(len(lines), 4)
            for line in lines:
                self.assertTrue(line["ok"])
            assert_matches_required_schema(self, lines[0]["result"], schema_def("claim_result"))
            assert_matches_required_schema(self, lines[1]["result"], schema_def("source_result"))
            assert_matches_required_schema(self, lines[2]["result"], schema_def("claim_result"))
            assert_matches_required_schema(self, lines[3]["result"], schema_def("relation_result"))
            self.assertEqual(lines[0]["result"]["type"], "fact")
            self.assertEqual(lines[1]["result"]["locator"], "doc.md")
            self.assertIn(old, lines[2]["result"]["supersedes"])
            self.assertEqual(lines[3]["result"]["relation"], "contradicts")

    def test_cli_error_details_are_schema_backed(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            run_cli("--path", str(kb), "init")
            request = json.dumps({"id": "bad-cite", "path": str(kb), "method": "akbp.cite", "params": {"claim_id": "missing"}}) + "\n"
            proc = subprocess.run([sys.executable, str(SERVER)], input=request, text=True, capture_output=True, check=True)
            line = json.loads(proc.stdout)
            assert_response_envelope(self, line)
            self.assertFalse(line["ok"])
            self.assertEqual(line["error"]["code"], "cli_error")
            assert_matches_required_schema(self, line["error"]["details"], schema_def("cli_error_details"))
            self.assertEqual(line["error"]["details"]["method"], "akbp.cite")
            self.assertEqual(line["error"]["details"]["exit_code"], 1)
            self.assertFalse(line["error"]["details"]["redacted"])


    def test_cli_error_redacts_stdout_and_message(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            run_cli("--path", str(kb), "init")
            secret = "sk-example123456789"
            request = json.dumps({"id": "bad-cite", "path": str(kb), "method": "akbp.cite", "params": {"claim_id": secret}}) + "\n"
            proc = subprocess.run([sys.executable, str(SERVER)], input=request, text=True, capture_output=True, check=True)
            line = json.loads(proc.stdout)
            assert_response_envelope(self, line)
            self.assertFalse(line["ok"])
            self.assertEqual(line["error"]["code"], "cli_error")
            self.assertNotIn(secret, proc.stdout)
            self.assertNotIn(secret, line["error"]["message"])
            self.assertNotIn(secret, line["error"]["details"]["stdout"])
            self.assertTrue(line["error"]["details"]["redacted"])

    def test_audit_cite_and_export_response_shapes(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            run_cli("--path", str(kb), "init")
            claim = json.loads(run_cli("--path", str(kb), "remember", "AKBP cite output has evidence", "--evidence", "AKBP.md").stdout)["id"]
            other_claim = json.loads(run_cli("--path", str(kb), "remember", "AKBP export can include relations", "--evidence", "REL.md").stdout)["id"]
            run_cli("--path", str(kb), "source", "add", "AKBP.md", "--title", "AKBP doc")
            run_cli("--path", str(kb), "contradict", claim, other_claim, "--evidence", "review.md")
            requests = "\n".join([
                json.dumps({"id": "cite", "path": str(kb), "method": "akbp.cite", "params": {"claim_id": claim}}),
                json.dumps({"id": "audit", "path": str(kb), "method": "akbp.audit", "params": {"limit": 5}}),
                json.dumps({"id": "export", "path": str(kb), "method": "akbp.export"}),
            ]) + "\n"
            proc = subprocess.run([sys.executable, str(SERVER)], input=requests, text=True, capture_output=True, check=True)
            lines = [json.loads(line) for line in proc.stdout.splitlines()]
            self.assertEqual(len(lines), 3)
            for line in lines:
                self.assertTrue(line["ok"])
            assert_matches_required_schema(self, lines[0]["result"], schema_def("cite_result"))
            assert_matches_required_schema(self, lines[1]["result"], schema_def("audit_result"))
            assert_matches_required_schema(self, lines[2]["result"], schema_def("export_result"))
            self.assertEqual(lines[0]["result"]["claim_id"], claim)
            self.assertGreaterEqual(lines[1]["result"]["count"], 2)
            self.assertTrue(lines[1]["result"]["events"])
            assert_matches_required_schema(self, lines[1]["result"]["events"][0], schema_def("audit_event"))
            self.assertEqual(lines[2]["result"]["manifest"]["format"], "akbp-portable-bundle")
            assert_matches_required_schema(self, lines[2]["result"]["manifest"], schema_def("export_manifest"))
            self.assertEqual(lines[2]["result"]["manifest"]["counts"]["claims"], len(lines[2]["result"]["claims"]))
            self.assertTrue(lines[2]["result"]["claims"])
            assert_matches_required_schema(self, lines[2]["result"]["claims"][0], schema_def("exported_claim"))
            self.assertTrue(lines[2]["result"]["sources"])
            assert_matches_required_schema(self, lines[2]["result"]["sources"][0], schema_def("source_result"))
            self.assertTrue(lines[2]["result"]["relations"])
            assert_matches_required_schema(self, lines[2]["result"]["relations"][0], schema_def("relation_result"))


    def test_source_verify_method_reports_file_drift(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            run_cli("--path", str(kb), "init")
            source = json.loads(run_cli("--path", str(kb), "source", "add", "AKBP.md", "--title", "AKBP doc").stdout)
            claim = json.loads(run_cli("--path", str(kb), "remember", "AKBP source verification reports dependent claims.", "--evidence", "AKBP.md").stdout)
            requests = "\n".join([
                json.dumps({"id": "source-ok", "path": str(kb), "method": "akbp.source.verify", "params": {"source_id": source["id"], "fail_on_issue": True}}),
            ]) + "\n"
            proc = subprocess.run([sys.executable, str(SERVER)], input=requests, text=True, capture_output=True, check=True)
            line = json.loads(proc.stdout)
            self.assertTrue(line["ok"])
            assert_matches_required_schema(self, line["result"], schema_def("source_verify_result"))
            self.assertTrue(line["result"]["ok"])
            self.assertEqual(line["result"]["counts"]["verified"], 1)
            (kb / "AKBP.md").write_text("changed", encoding="utf-8")
            request = json.dumps({"id": "source-changed", "path": str(kb), "method": "akbp.source.verify", "params": {"source_id": source["id"], "fail_on_issue": True}}) + "\n"
            proc = subprocess.run([sys.executable, str(SERVER)], input=request, text=True, capture_output=True, check=True)
            line = json.loads(proc.stdout)
            self.assertTrue(line["ok"])
            self.assertFalse(line["result"]["ok"])
            self.assertEqual(line["result"]["counts"]["changed"], 1)
            self.assertEqual(line["result"]["changed"][0]["affected_claims"], [claim["id"]])
            self.assertEqual(line["result"]["attention"]["recommended_action"], "review_affected_claims")
            self.assertEqual(line["result"]["attention"]["changed_source_ids"], [source["id"]])
            self.assertEqual(line["result"]["attention"]["affected_claims"], [claim["id"]])

    def test_export_check_method_validates_bundle_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            run_cli("--path", str(kb), "init")
            run_cli("--path", str(kb), "source", "add", "AKBP.md", "--title", "AKBP doc")
            run_cli("--path", str(kb), "remember", "AKBP exports have checkable manifests", "--evidence", "AKBP.md")
            bundle = Path(d) / "bundle.json"
            bundle.write_text(run_cli("--path", str(kb), "export").stdout, encoding="utf-8")
            request = json.dumps({"id": "export-check", "path": str(kb), "method": "akbp.export_check", "params": {"file": str(bundle), "fail_on_issues": True}}) + "\n"
            proc = subprocess.run([sys.executable, str(SERVER)], input=request, text=True, capture_output=True, check=True)
            line = json.loads(proc.stdout)
            self.assertTrue(line["ok"])
            assert_matches_required_schema(self, line["result"], schema_def("export_check_result"))
            self.assertTrue(line["result"]["ok"])
            self.assertEqual(line["result"]["issues"], [])

            invalid_bundle = Path(d) / "invalid-bundle.json"
            invalid_bundle.write_text(json.dumps({
                "akbp_version": "0.1.0",
                "exported_at": "2026-05-08T12:00:00Z",
                "card": {},
                "claims": [],
                "sources": [],
                "entities": [],
                "relations": [],
                "manifest": {
                    "format": "akbp-portable-bundle",
                    "counts": {"claims": 1, "sources": 0, "entities": 0, "relations": 0},
                    "artifact_hashes": {"card": "not-a-hash", "claims": None, "sources": None, "entities": None, "relations": None},
                    "safety": {"excludes_local_state": False, "excludes_indexes": True, "secret_redaction_required": True},
                },
            }), encoding="utf-8")
            strict_request = json.dumps({"id": "export-check-strict", "path": str(kb), "method": "akbp.export_check", "params": {"file": str(invalid_bundle), "fail_on_issues": True}}) + "\n"
            strict_proc = subprocess.run([sys.executable, str(SERVER)], input=strict_request, text=True, capture_output=True, check=True)
            strict_line = json.loads(strict_proc.stdout)
            self.assertTrue(strict_line["ok"])
            assert_matches_required_schema(self, strict_line["result"], schema_def("export_check_result"))
            self.assertFalse(strict_line["result"]["ok"])
            self.assertEqual({issue["code"] for issue in strict_line["result"]["issues"]}, {"count_mismatch", "invalid_artifact_hash", "unsafe_manifest"})

    def test_import_check_method_validates_jsonl_without_echoing_secret(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            export = Path(d) / "export.jsonl"
            export.write_text(
                json.dumps({"kind": "claim", "id": "claim_safe", "text": "Safe imported claim."}) + "\n" +
                json.dumps({"kind": "claim", "id": "claim_unsafe", "text": "Copied token=sk-example123456789 into output."}) + "\n",
                encoding="utf-8",
            )
            request = json.dumps({
                "id": "import-check",
                "path": str(kb),
                "method": "akbp.import_check",
                "params": {"file": str(export)},
            }) + "\n"
            proc = subprocess.run([sys.executable, str(SERVER)], input=request, text=True, capture_output=True, check=True)
            line = json.loads(proc.stdout)
            self.assertTrue(line["ok"])
            assert_matches_required_schema(self, line["result"], schema_def("import_check_result"))
            self.assertEqual(line["result"]["accepted_count"], 1)
            self.assertEqual(line["result"]["rejected_count"], 1)
            self.assertEqual(line["result"]["error_count"], 0)
            self.assertFalse(line["result"]["fail_on_rejected"])
            self.assertEqual([item["id"] for item in line["result"]["accepted"]], ["claim_safe"])
            self.assertEqual([item["id"] for item in line["result"]["rejected"]], ["claim_unsafe"])
            self.assertNotIn("sk-example123456789", proc.stdout)

            strict_request = json.dumps({
                "id": "import-check-strict",
                "path": str(kb),
                "method": "akbp.import_check",
                "params": {"file": str(export), "fail_on_rejected": True},
            }) + "\n"
            strict_proc = subprocess.run([sys.executable, str(SERVER)], input=strict_request, text=True, capture_output=True, check=True)
            strict_line = json.loads(strict_proc.stdout)
            self.assertTrue(strict_line["ok"])
            assert_matches_required_schema(self, strict_line["result"], schema_def("import_check_result"))
            self.assertFalse(strict_line["result"]["ok"])
            self.assertTrue(strict_line["result"]["fail_on_rejected"])
            self.assertEqual(strict_line["result"]["rejected_count"], 1)
            self.assertNotIn("sk-example123456789", strict_proc.stdout)

    def test_import_apply_failure_result_matches_schema(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            run_cli("--path", str(kb), "init")
            export = Path(d) / "unsafe-export.jsonl"
            export.write_text(
                json.dumps({"kind": "claim", "id": "claim_tool_unsafe", "text": "token=sk-example123456789", "type": "workflow", "status": "working", "confidence": 0.7, "evidence": []}) + "\n",
                encoding="utf-8",
            )
            request = json.dumps({"id": "bad-import", "path": str(kb), "method": "akbp.import_apply", "dry_run": True, "params": {"file": str(export)}}) + "\n"
            proc = subprocess.run([sys.executable, str(SERVER)], input=request, text=True, capture_output=True, check=True)
            line = json.loads(proc.stdout)
            self.assertTrue(line["ok"])
            self.assertFalse(line["result"]["ok"])
            assert_matches_required_schema(self, line["result"], schema_def("import_apply_result"))
            self.assertEqual(line["result"]["would_write"], {"sources": [], "claims": []})
            self.assertNotIn("sk-example123456789", proc.stdout)

    def test_import_apply_method_previews_and_applies_after_approval(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            run_cli("--path", str(kb), "init")
            export = Path(d) / "safe-export.jsonl"
            export.write_text(
                json.dumps({"kind": "source", "id": "source_tool_import", "type": "transcript", "locator": "imports/tool.md", "title": "Tool import"}) + "\n" +
                json.dumps({"kind": "claim", "id": "claim_tool_import", "text": "JSONL tool import apply writes reviewed objects.", "type": "workflow", "status": "working", "confidence": 0.8, "evidence": ["source_tool_import"], "scope": "project"}) + "\n",
                encoding="utf-8",
            )
            requests = "\n".join([
                json.dumps({"id": "preview", "path": str(kb), "method": "akbp.import_apply", "dry_run": True, "params": {"file": str(export)}}),
                json.dumps({"id": "blocked", "path": str(kb), "method": "akbp.import_apply", "params": {"file": str(export)}}),
                json.dumps({"id": "apply", "path": str(kb), "method": "akbp.import_apply", "approved": True, "params": {"file": str(export)}}),
            ]) + "\n"
            proc = subprocess.run([sys.executable, str(SERVER)], input=requests, text=True, capture_output=True, check=True)
            lines = [json.loads(line) for line in proc.stdout.splitlines()]
            self.assertTrue(lines[0]["ok"])
            assert_matches_required_schema(self, lines[0]["result"], schema_def("import_apply_result"))
            self.assertTrue(lines[0]["result"]["dry_run"])
            self.assertFalse(lines[0]["result"]["applied"])
            self.assertEqual(lines[0]["result"]["would_write"]["claims"], ["claim_tool_import"])
            self.assertTrue(lines[0]["result"]["review_required"])
            self.assertIn("--approved", lines[0]["result"]["apply_instruction"])
            self.assertFalse(lines[1]["ok"])
            self.assertEqual(lines[1]["error"]["code"], "approval_required")
            self.assertTrue(lines[2]["ok"])
            assert_matches_required_schema(self, lines[2]["result"], schema_def("import_apply_result"))
            self.assertTrue(lines[2]["result"]["applied"])
            claims = [json.loads(line) for line in (kb / "claims" / "claims.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertIn("claim_tool_import", {claim["id"] for claim in claims})

    def test_ingest_method_imports_file(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            note = Path(d) / "note.md"
            note.write_text("# Note\n\nDecision: keep imports redacted.\ntoken=sk-example123456789\n", encoding="utf-8")
            run_cli("--path", str(kb), "init")
            request = json.dumps({
                "id": "ingest",
                "path": str(kb),
                "method": "akbp.ingest",
                "approved": True,
                "params": {
                    "file": str(note),
                    "claim": "Imported notes should be redacted.",
                    "claim_type": "decision",
                },
            }) + "\n"
            proc = subprocess.run([sys.executable, str(SERVER)], input=request, text=True, capture_output=True, check=True)
            line = json.loads(proc.stdout)
            self.assertTrue(line["ok"])
            self.assertTrue(line["result"]["redacted"])
            assert_matches_required_schema(self, line["result"], schema_def("ingest_result"))
            page = kb / line["result"]["page"]
            self.assertIn("[REDACTED]", page.read_text(encoding="utf-8"))
            claims = [json.loads(row) for row in (kb / "claims" / "claims.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertNotIn("sk-example123456789", claims[0]["text"])


    def test_source_add_redacts_secret_like_title(self):
        with tempfile.TemporaryDirectory() as tmp:
            note = Path(tmp) / "note.md"
            note.write_text("# Note\n", encoding="utf-8")
            requests = json.dumps({
                "id": "source-add",
                "method": "akbp.source.add",
                "path": tmp,
                "approved": True,
                "params": {
                    "locator": str(note),
                    "type": "file",
                    "title": "Incident api_key=sk-live-demo",
                },
            }) + "\n"
            proc = subprocess.run([sys.executable, str(SERVER)], input=requests, text=True, capture_output=True, check=True)
            line = json.loads(proc.stdout)
            self.assertTrue(line["ok"])
            self.assertEqual(line["result"]["title"], "Incident [REDACTED]")
            self.assertNotIn("sk-live-demo", json.dumps(line))

    def test_ingest_dry_run_returns_redacted_preview(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            note = Path(d) / "note.md"
            note.write_text("# Preview Note\n\nDecision: dry-run before import.\napi_key=sk-example123456789\n", encoding="utf-8")
            request = json.dumps({
                "id": "ingest-dry",
                "path": str(kb),
                "method": "akbp.ingest",
                "dry_run": True,
                "params": {
                    "file": str(note),
                    "claim": "Preview import after token=sk-example123456789 appears.",
                    "claim_type": "warning",
                },
            }) + "\n"
            proc = subprocess.run([sys.executable, str(SERVER)], input=request, text=True, capture_output=True, check=True)
            line = json.loads(proc.stdout)
            self.assertTrue(line["ok"])
            self.assertTrue(line["result"]["dry_run"])
            self.assertTrue(line["result"]["review_required"])
            self.assertIn("redaction", line["result"]["apply_instruction"])
            self.assertTrue(line["result"]["redacted"])
            self.assertIn("claims/claims.jsonl", line["result"]["would_write"])
            assert_matches_required_schema(self, line["result"], schema_def("ingest_dry_run_result"))
            self.assertFalse((kb / "claims" / "claims.jsonl").exists())
            self.assertFalse((kb / line["result"]["page"]).exists())

    def test_adapter_session_start_and_end_methods(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            transcript = Path(d) / "session.md"
            transcript.write_text("# Session\n\nDecision: adapters should expose session lifecycle operations.\n", encoding="utf-8")
            run_cli("--path", str(kb), "init")
            run_cli("--path", str(kb), "remember", "Adapters retrieve context at session start", "--type", "workflow", "--evidence", "AKBP.md")
            requests = "\n".join([
                json.dumps({"id": "start", "path": str(kb), "method": "akbp.session.start", "params": {"task": "adapter session lifecycle", "limit": 5}}),
                json.dumps({"id": "end-preview", "path": str(kb), "method": "akbp.session.end", "dry_run": True, "params": {"transcript": str(transcript), "apply": True}}),
                json.dumps({"id": "end-apply", "path": str(kb), "method": "akbp.session.end", "approved": True, "params": {"transcript": str(transcript), "apply": True}}),
            ]) + "\n"
            proc = subprocess.run([sys.executable, str(SERVER)], input=requests, text=True, capture_output=True, check=True)
            lines = [json.loads(line) for line in proc.stdout.splitlines()]
            self.assertEqual([line["id"] for line in lines], ["start", "end-preview", "end-apply"])
            self.assertTrue(lines[0]["ok"])
            assert_matches_required_schema(self, lines[0]["result"], schema_def("session_start_result"))
            self.assertEqual(lines[0]["result"]["task"], "adapter session lifecycle")
            self.assertTrue(lines[1]["ok"])
            assert_matches_required_schema(self, lines[1]["result"], schema_def("session_end_preview_result"))
            self.assertFalse(lines[1]["result"]["apply"])
            self.assertTrue(lines[1]["result"]["review_required"])
            self.assertTrue(lines[2]["ok"])
            assert_matches_required_schema(self, lines[2]["result"], schema_def("crystallize_session_result"))
            self.assertTrue(lines[2]["result"]["apply"])
            self.assertTrue((kb / lines[2]["result"]["page"]).exists())

    def test_crystallize_session_method(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            transcript = Path(d) / "session.md"
            transcript.write_text("# Session\n\nDecision: keep agent knowledge portable.\n", encoding="utf-8")
            run_cli("--path", str(kb), "init")
            dry_request = json.dumps({"id": "dry", "path": str(kb), "method": "akbp.crystallize_session", "dry_run": True, "params": {"transcript": str(transcript), "apply": True}}) + "\n"
            proc = subprocess.run([sys.executable, str(SERVER)], input=dry_request, text=True, capture_output=True, check=True)
            dry = json.loads(proc.stdout)
            self.assertTrue(dry["ok"])
            self.assertTrue(dry["result"]["dry_run"])
            self.assertFalse(dry["result"]["apply"])
            self.assertTrue(dry["result"]["review_required"])
            self.assertIn("summary", dry["result"])
            assert_matches_required_schema(self, dry["result"], schema_def("session_end_preview_result"))
            self.assertFalse((kb / dry["result"]["page"]).exists())

            apply_request = json.dumps({"id": "apply", "path": str(kb), "method": "akbp.crystallize_session", "approved": True, "params": {"transcript": str(transcript), "apply": True}}) + "\n"
            proc = subprocess.run([sys.executable, str(SERVER)], input=apply_request, text=True, capture_output=True, check=True)
            applied = json.loads(proc.stdout)
            self.assertTrue(applied["ok"])
            assert_matches_required_schema(self, applied["result"], schema_def("crystallize_session_result"))
            self.assertTrue(applied["result"]["created_claims"])


    def test_invalid_request_envelope_is_structured_before_dispatch(self):
        requests = "\n".join([
            json.dumps({"method": "akbp.status"}),
            json.dumps({"id": "bad-method", "method": "status"}),
            json.dumps({"id": "bad-dry", "method": "akbp.status", "dry_run": "yes"}),
            json.dumps({"id": "bad-approved", "method": "akbp.status", "approved": "yes"}),
        ]) + "\n"
        proc = subprocess.run([sys.executable, str(SERVER)], input=requests, text=True, capture_output=True, check=True)
        lines = [json.loads(line) for line in proc.stdout.splitlines()]
        self.assertEqual([line["error"]["code"] for line in lines], ["invalid_request"] * 4)
        self.assertIn("tool-request.schema.json", lines[0]["error"]["details"]["schema"])
        self.assertIn("missing required field: id", lines[0]["error"]["details"]["errors"])
        self.assertIn("method must be an akbp.* string", lines[1]["error"]["details"]["errors"])
        self.assertIn("dry_run must be a boolean", lines[2]["error"]["details"]["errors"])
        self.assertIn("approved must be a boolean", lines[3]["error"]["details"]["errors"])

    def test_structured_errors(self):
        requests = json.dumps({"id": "bad", "method": "akbp.missing"}) + "\n"
        proc = subprocess.run([sys.executable, str(SERVER)], input=requests, text=True, capture_output=True, check=True)
        line = json.loads(proc.stdout)
        self.assertFalse(line["ok"])
        self.assertEqual(line["error"]["code"], "unknown_method")
        self.assertIn("available_methods", line["error"]["details"])

    def test_path_like_string_params_reject_control_chars_before_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            requests = "\n".join([
                json.dumps({
                    "id": "bad-file",
                    "method": "akbp.import_check",
                    "path": tmp,
                    "params": {"file": "import\n.jsonl"},
                }),
                json.dumps({
                    "id": "bad-locator",
                    "method": "akbp.source.add",
                    "path": tmp,
                    "dry_run": True,
                    "params": {"locator": "docs/notes\r.md"},
                }),
            ]) + "\n"
            proc = subprocess.run([sys.executable, str(SERVER)], input=requests, text=True, capture_output=True, check=True)
            rows = [json.loads(line) for line in proc.stdout.splitlines()]
        for row in rows:
            self.assertFalse(row["ok"])
            self.assertEqual(row["error"]["code"], "invalid_params")
            assert_matches_required_schema(self, row["error"]["details"], schema_def("invalid_params_details"))
        self.assertIn("file must not contain control characters", rows[0]["error"]["details"]["type_errors"])
        self.assertIn("locator must not contain control characters", rows[1]["error"]["details"]["type_errors"])

    def test_oversized_string_params_are_structured_before_cli(self):
        with tempfile.TemporaryDirectory() as d:
            requests = "\n".join([
                json.dumps({"id": "too-long-query", "method": "akbp.search", "path": d, "params": {"query": "x" * 4097}}),
                json.dumps({"id": "too-long-export-check-file", "method": "akbp.export_check", "path": d, "params": {"file": "x" * 4097}}),
                json.dumps({"id": "too-long-import-check-file", "method": "akbp.import_check", "path": d, "params": {"file": "x" * 4097}}),
                json.dumps({"id": "too-long-import-apply-file", "method": "akbp.import_apply", "path": d, "dry_run": True, "params": {"file": "x" * 4097}}),
            ]) + "\n"
            proc = subprocess.run([sys.executable, str(SERVER)], input=requests, text=True, capture_output=True, check=True)
            lines = [json.loads(line) for line in proc.stdout.splitlines()]
            self.assertEqual(len(lines), 4)
            for line in lines:
                self.assertFalse(line["ok"])
                self.assertEqual(line["error"]["code"], "invalid_params")
                assert_matches_required_schema(self, line["error"]["details"], schema_def("invalid_params_details"))
            self.assertIn("query must be at most 4096 characters", lines[0]["error"]["details"]["type_errors"])
            self.assertIn("file must be at most 4096 characters", lines[1]["error"]["details"]["type_errors"])
            self.assertIn("file must be at most 4096 characters", lines[2]["error"]["details"]["type_errors"])
            self.assertIn("file must be at most 4096 characters", lines[3]["error"]["details"]["type_errors"])
            self.assertTrue(lines[1]["error"]["details"]["params_schema"].endswith("#/$defs/akbp.export_check.params"))
            self.assertTrue(lines[2]["error"]["details"]["params_schema"].endswith("#/$defs/akbp.import_check.params"))
            self.assertTrue(lines[3]["error"]["details"]["params_schema"].endswith("#/$defs/akbp.import_apply.params"))

    def test_empty_string_params_are_structured_before_cli(self):
        requests = "\n".join([
            json.dumps({"id": "blank-session-query", "method": "akbp.session.start", "params": {"query": "   "}}),
            json.dumps({"id": "blank-session-task", "method": "akbp.session.start", "params": {"task": ""}}),
        ]) + "\n"
        proc = subprocess.run([sys.executable, str(SERVER)], input=requests, text=True, capture_output=True, check=True)
        lines = [json.loads(line) for line in proc.stdout.splitlines()]
        self.assertEqual(len(lines), 2)
        for line in lines:
            self.assertFalse(line["ok"])
            self.assertEqual(line["error"]["code"], "invalid_params")
            assert_matches_required_schema(self, line["error"]["details"], schema_def("invalid_params_details"))
        self.assertIn("query must not be empty", lines[0]["error"]["details"]["type_errors"])
        self.assertIn("task must not be empty", lines[1]["error"]["details"]["type_errors"])

    def test_evidence_and_entity_arrays_are_bounded_before_cli(self):
        requests = "\n".join([
            json.dumps({"id": "too-many-evidence", "method": "akbp.remember", "params": {"text": "x", "evidence": ["source_ok"] * 65}}),
            json.dumps({"id": "long-evidence", "method": "akbp.remember", "params": {"text": "x", "evidence": ["e" * 513]}}),
            json.dumps({"id": "bad-entity-control", "method": "akbp.ingest", "params": {"file": "notes.md", "entity": ["agent\nname"]}}),
        ]) + "\n"
        proc = subprocess.run([sys.executable, str(SERVER)], input=requests, text=True, capture_output=True, check=True)
        lines = [json.loads(line) for line in proc.stdout.splitlines()]
        self.assertEqual(len(lines), 3)
        for line in lines:
            self.assertFalse(line["ok"])
            self.assertEqual(line["error"]["code"], "invalid_params")
            assert_matches_required_schema(self, line["error"]["details"], schema_def("invalid_params_details"))
        self.assertIn("evidence must contain at most 64 items", lines[0]["error"]["details"]["type_errors"])
        self.assertIn("evidence[0] must be at most 512 characters", lines[1]["error"]["details"]["type_errors"])
        self.assertIn("entity[0] must not contain control characters", lines[2]["error"]["details"]["type_errors"])

    def test_invalid_params_are_structured_before_cli(self):
        requests = "\n".join([
            json.dumps({"id": "shape", "method": "akbp.search", "params": "not an object"}),
            json.dumps({"id": "unknown", "method": "akbp.search", "params": {"query": "release", "surprise": True}}),
            json.dumps({"id": "capabilities-unknown", "method": "akbp.capabilities", "params": {"surprise": True}}),
            json.dumps({"id": "missing", "method": "akbp.crystallize_session", "dry_run": True, "params": {"transcript": ""}}),
            json.dumps({"id": "bad-param-dry", "method": "akbp.remember", "params": {"text": "x", "dry_run": "yes"}}),
            json.dumps({"id": "bad-limit", "method": "akbp.search", "params": {"query": "release", "limit": "5"}}),
            json.dumps({"id": "bad-apply", "method": "akbp.crystallize_session", "params": {"transcript": "session.md", "apply": "true"}}),
            json.dumps({"id": "bad-query", "method": "akbp.search", "params": {"query": 123}}),
            json.dumps({"id": "bad-confidence", "method": "akbp.ingest", "params": {"file": "notes.md", "confidence": "high"}}),
            json.dumps({"id": "bad-evidence-item", "method": "akbp.remember", "params": {"text": "x", "evidence": ["source_ok", 42]}}),
            json.dumps({"id": "bad-entity-item", "method": "akbp.ingest", "params": {"file": "notes.md", "entity": ["agent", False]}}),
            json.dumps({"id": "bad-limit-range", "method": "akbp.search", "params": {"query": "release", "limit": 0}}),
            json.dumps({"id": "bad-confidence-range", "method": "akbp.ingest", "params": {"file": "notes.md", "confidence": 1.5}}),
            json.dumps({"id": "bad-claim-type", "method": "akbp.remember", "params": {"text": "x", "type": "unknown"}}),
            json.dumps({"id": "bad-source-type", "method": "akbp.source.add", "params": {"locator": "notes.md", "type": "binary"}}),
            json.dumps({"id": "bad-ingest-claim-type", "method": "akbp.ingest", "params": {"file": "notes.md", "claim_type": "blocker"}}),
        ]) + "\n"
        proc = subprocess.run([sys.executable, str(SERVER)], input=requests, text=True, capture_output=True, check=True)
        lines = [json.loads(line) for line in proc.stdout.splitlines()]
        self.assertEqual(lines[0]["error"]["code"], "invalid_params")
        self.assertEqual(lines[0]["error"]["message"], "params must be an object")
        self.assertTrue(lines[0]["error"]["details"]["params_schema"].endswith("#/$defs/akbp.search.params"))
        self.assertIn("params must be an object", lines[0]["error"]["details"]["type_errors"])
        assert_matches_required_schema(self, lines[0]["error"]["details"], schema_def("invalid_params_details"))
        self.assertEqual(lines[1]["error"]["code"], "invalid_params")
        self.assertEqual(lines[1]["error"]["details"]["unknown"], ["surprise"])
        self.assertIn("query", lines[1]["error"]["details"]["allowed"])
        self.assertTrue(lines[1]["error"]["details"]["params_schema"].endswith("#/$defs/akbp.search.params"))
        self.assertEqual(lines[2]["error"]["code"], "invalid_params")
        self.assertEqual(lines[2]["error"]["details"]["unknown"], ["surprise"])
        self.assertEqual(lines[2]["error"]["details"]["allowed"], ["client", "requires", "requires_profiles", "requires_methods"])
        self.assertTrue(lines[2]["error"]["details"]["params_schema"].endswith("#/$defs/akbp.capabilities.params"))
        self.assertEqual(lines[3]["error"]["code"], "invalid_params")
        self.assertEqual(lines[3]["error"]["details"]["missing"], ["transcript"])
        self.assertTrue(lines[3]["error"]["details"]["params_schema"].endswith("#/$defs/akbp.crystallize_session.params"))
        self.assertEqual(lines[4]["error"]["code"], "invalid_params")
        self.assertIn("dry_run must be a boolean", lines[4]["error"]["details"]["type_errors"])
        self.assertIn("limit must be an integer", lines[5]["error"]["details"]["type_errors"])
        self.assertIn("apply must be a boolean", lines[6]["error"]["details"]["type_errors"])
        self.assertIn("query must be a string", lines[7]["error"]["details"]["type_errors"])
        self.assertIn("confidence must be a finite number", lines[8]["error"]["details"]["type_errors"])
        self.assertIn("evidence items must be strings", lines[9]["error"]["details"]["type_errors"])
        self.assertIn("entity items must be strings", lines[10]["error"]["details"]["type_errors"])
        self.assertIn("limit must be between 1 and 100", lines[11]["error"]["details"]["type_errors"])
        self.assertIn("confidence must be between 0 and 1", lines[12]["error"]["details"]["type_errors"])
        self.assertIn("type must be one of:", lines[13]["error"]["details"]["type_errors"][0])
        self.assertIn("warning", lines[13]["error"]["details"]["type_errors"][0])
        self.assertIn("type must be one of:", lines[14]["error"]["details"]["type_errors"][0])
        self.assertIn("transcript", lines[14]["error"]["details"]["type_errors"][0])
        self.assertIn("claim_type must be one of:", lines[15]["error"]["details"]["type_errors"][0])
        for line in lines[3:]:
            assert_matches_required_schema(self, line["error"]["details"], schema_def("invalid_params_details"))


    def test_numeric_params_reject_parser_overflow_before_dispatch(self):
        proc = subprocess.run(
            [sys.executable, str(SERVER)],
            input='{"id":"overflow","method":"akbp.ingest","params":{"file":"notes.md","confidence":1e999}}\n',
            text=True,
            capture_output=True,
            check=True,
        )
        line = json.loads(proc.stdout)
        assert_response_envelope(self, line)
        self.assertFalse(line["ok"])
        self.assertEqual(line["error"]["code"], "invalid_params")
        self.assertIn("confidence must be a finite number", line["error"]["details"]["type_errors"])
        self.assertTrue(line["error"]["details"]["params_schema"].endswith("#/$defs/akbp.ingest.params"))
        assert_matches_required_schema(self, line["error"]["details"], schema_def("invalid_params_details"))

    def test_array_param_errors_report_method_schemas(self):
        requests = "\n".join([
            json.dumps({"id": "bad-remember-evidence", "method": "akbp.remember", "params": {"text": "x", "evidence": [42]}}),
            json.dumps({"id": "bad-ingest-entity", "method": "akbp.ingest", "params": {"file": "notes.md", "entity": [False]}}),
        ]) + "\n"
        proc = subprocess.run([sys.executable, str(SERVER)], input=requests, text=True, capture_output=True, check=True)
        lines = [json.loads(line) for line in proc.stdout.splitlines()]
        self.assertEqual([line["error"]["code"] for line in lines], ["invalid_params"] * 2)
        self.assertIn("evidence items must be strings", lines[0]["error"]["details"]["type_errors"])
        self.assertTrue(lines[0]["error"]["details"]["params_schema"].endswith("#/$defs/akbp.remember.params"))
        self.assertIn("entity items must be strings", lines[1]["error"]["details"]["type_errors"])
        self.assertTrue(lines[1]["error"]["details"]["params_schema"].endswith("#/$defs/akbp.ingest.params"))
        for line in lines:
            assert_matches_required_schema(self, line["error"]["details"], schema_def("invalid_params_details"))

    def test_enum_param_errors_report_method_schemas(self):
        requests = "\n".join([
            json.dumps({"id": "bad-remember-type", "method": "akbp.remember", "params": {"text": "x", "type": "blocker"}}),
            json.dumps({"id": "bad-source-type", "method": "akbp.source.add", "params": {"locator": "notes.md", "type": "binary"}}),
            json.dumps({"id": "bad-ingest-claim-type", "method": "akbp.ingest", "params": {"file": "notes.md", "claim_type": "blocker"}}),
            json.dumps({"id": "bad-conformance-level", "method": "akbp.conformance", "params": {"level": "4"}}),
        ]) + "\n"
        proc = subprocess.run([sys.executable, str(SERVER)], input=requests, text=True, capture_output=True, check=True)
        lines = [json.loads(line) for line in proc.stdout.splitlines()]
        expected = [
            ("type must be one of:", "#/$defs/akbp.remember.params"),
            ("type must be one of:", "#/$defs/akbp.source.add.params"),
            ("claim_type must be one of:", "#/$defs/akbp.ingest.params"),
            ("level must be one of:", "#/$defs/akbp.conformance.params"),
        ]
        self.assertEqual([line["error"]["code"] for line in lines], ["invalid_params"] * 4)
        for line, (message, schema_ref) in zip(lines, expected):
            self.assertIn(message, line["error"]["details"]["type_errors"][0])
            self.assertTrue(line["error"]["details"]["params_schema"].endswith(schema_ref))
            assert_matches_required_schema(self, line["error"]["details"], schema_def("invalid_params_details"))

    def test_boolean_param_errors_report_method_schemas(self):
        requests = "\n".join([
            json.dumps({"id": "bad-index-incremental", "method": "akbp.index", "params": {"incremental": "yes"}}),
            json.dumps({"id": "bad-export-check-flag", "method": "akbp.export_check", "params": {"file": "bundle.jsonl", "fail_on_issues": "yes"}}),
            json.dumps({"id": "bad-import-check-flag", "method": "akbp.import_check", "params": {"file": "bundle.jsonl", "fail_on_rejected": "yes"}}),
            json.dumps({"id": "bad-source-verify-flag", "method": "akbp.source.verify", "params": {"source_id": "source_ok", "fail_on_issue": "yes"}}),
        ]) + "\n"
        proc = subprocess.run([sys.executable, str(SERVER)], input=requests, text=True, capture_output=True, check=True)
        lines = [json.loads(line) for line in proc.stdout.splitlines()]
        expected = [
            ("incremental must be a boolean", "#/$defs/akbp.index.params"),
            ("fail_on_issues must be a boolean", "#/$defs/akbp.export_check.params"),
            ("fail_on_rejected must be a boolean", "#/$defs/akbp.import_check.params"),
            ("fail_on_issue must be a boolean", "#/$defs/akbp.source.verify.params"),
        ]
        self.assertEqual([line["error"]["code"] for line in lines], ["invalid_params"] * 4)
        for line, (message, schema_ref) in zip(lines, expected):
            self.assertIn(message, line["error"]["details"]["type_errors"])
            self.assertTrue(line["error"]["details"]["params_schema"].endswith(schema_ref))
            assert_matches_required_schema(self, line["error"]["details"], schema_def("invalid_params_details"))

    def test_relation_partial_missing_params_report_method_schemas(self):
        requests = "\n".join([
            json.dumps({"id": "missing-supersede-text", "method": "akbp.supersede", "params": {"old_claim_id": "claim_old"}}),
            json.dumps({"id": "missing-contradict-target", "method": "akbp.contradict", "params": {"source_claim_id": "claim_a"}}),
        ]) + "\n"
        proc = subprocess.run([sys.executable, str(SERVER)], input=requests, text=True, capture_output=True, check=True)
        lines = [json.loads(line) for line in proc.stdout.splitlines()]
        self.assertEqual([line["error"]["code"] for line in lines], ["invalid_params"] * 2)
        self.assertEqual(lines[0]["error"]["details"]["missing"], ["text"])
        self.assertTrue(lines[0]["error"]["details"]["params_schema"].endswith("#/$defs/akbp.supersede.params"))
        self.assertEqual(lines[1]["error"]["details"]["missing"], ["target_claim_id"])
        self.assertTrue(lines[1]["error"]["details"]["params_schema"].endswith("#/$defs/akbp.contradict.params"))
        for line in lines:
            assert_matches_required_schema(self, line["error"]["details"], schema_def("invalid_params_details"))

    def test_file_and_source_missing_params_report_method_schemas(self):
        requests = "\n".join([
            json.dumps({"id": "missing-export-check", "method": "akbp.export_check", "params": {}}),
            json.dumps({"id": "missing-import-check", "method": "akbp.import_check", "params": {}}),
            json.dumps({"id": "missing-source-verify", "method": "akbp.source.verify", "params": {}}),
        ]) + "\n"
        proc = subprocess.run([sys.executable, str(SERVER)], input=requests, text=True, capture_output=True, check=True)
        lines = [json.loads(line) for line in proc.stdout.splitlines()]
        self.assertEqual([line["error"]["code"] for line in lines], ["invalid_params"] * 3)
        self.assertEqual(lines[0]["error"]["details"]["missing"], ["file"])
        self.assertTrue(lines[0]["error"]["details"]["params_schema"].endswith("#/$defs/akbp.export_check.params"))
        self.assertEqual(lines[1]["error"]["details"]["missing"], ["file"])
        self.assertTrue(lines[1]["error"]["details"]["params_schema"].endswith("#/$defs/akbp.import_check.params"))
        self.assertEqual(lines[2]["error"]["details"]["missing"], ["source_id"])
        self.assertTrue(lines[2]["error"]["details"]["params_schema"].endswith("#/$defs/akbp.source.verify.params"))
        for line in lines:
            assert_matches_required_schema(self, line["error"]["details"], schema_def("invalid_params_details"))

    def test_session_end_missing_transcript_reports_lifecycle_schema(self):
        request = json.dumps({"id": "missing-session-end", "method": "akbp.session.end", "dry_run": True, "params": {}}) + "\n"
        proc = subprocess.run([sys.executable, str(SERVER)], input=request, text=True, capture_output=True, check=True)
        line = json.loads(proc.stdout)
        self.assertEqual(line["error"]["code"], "invalid_params")
        self.assertEqual(line["error"]["details"]["missing"], ["transcript"])
        self.assertTrue(line["error"]["details"]["params_schema"].endswith("#/$defs/akbp.session.end.params"))
        assert_matches_required_schema(self, line["error"]["details"], schema_def("invalid_params_details"))

    def test_session_start_limit_error_reports_lifecycle_schema(self):
        request = json.dumps({"id": "bad-session-start", "method": "akbp.session.start", "params": {"task": "adapter lifecycle", "limit": 0}}) + "\n"
        proc = subprocess.run([sys.executable, str(SERVER)], input=request, text=True, capture_output=True, check=True)
        line = json.loads(proc.stdout)
        self.assertEqual(line["error"]["code"], "invalid_params")
        self.assertIn("limit must be between 1 and 100", line["error"]["details"]["type_errors"])
        self.assertTrue(line["error"]["details"]["params_schema"].endswith("#/$defs/akbp.session.start.params"))
        assert_matches_required_schema(self, line["error"]["details"], schema_def("invalid_params_details"))

    def test_read_method_limit_errors_report_method_schemas(self):
        requests = "\n".join([
            json.dumps({"id": "bad-query-limit", "method": "akbp.query", "params": {"query": "release notes", "limit": False}}),
            json.dumps({"id": "bad-context-limit", "method": "akbp.context", "params": {"task": "adapter lifecycle", "limit": 101}}),
            json.dumps({"id": "bad-audit-limit", "method": "akbp.audit", "params": {"limit": "20"}}),
            json.dumps({"id": "bad-context-budget", "method": "akbp.context", "params": {"task": "adapter lifecycle", "max_chars": 0}}),
            json.dumps({"id": "bad-context-min-items", "method": "akbp.context", "params": {"task": "adapter lifecycle", "min_items": 101}}),
        ]) + "\n"
        proc = subprocess.run([sys.executable, str(SERVER)], input=requests, text=True, capture_output=True, check=True)
        lines = [json.loads(line) for line in proc.stdout.splitlines()]
        self.assertEqual([line["error"]["code"] for line in lines], ["invalid_params"] * 5)
        self.assertIn("limit must be an integer", lines[0]["error"]["details"]["type_errors"])
        self.assertIn("limit must be between 1 and 100", lines[1]["error"]["details"]["type_errors"])
        self.assertIn("limit must be an integer", lines[2]["error"]["details"]["type_errors"])
        self.assertIn("max_chars must be between 1 and 65536", lines[3]["error"]["details"]["type_errors"])
        self.assertIn("min_items must be between 0 and 100", lines[4]["error"]["details"]["type_errors"])
        self.assertTrue(lines[0]["error"]["details"]["params_schema"].endswith("#/$defs/akbp.query.params"))
        self.assertTrue(lines[1]["error"]["details"]["params_schema"].endswith("#/$defs/akbp.context.params"))
        self.assertTrue(lines[2]["error"]["details"]["params_schema"].endswith("#/$defs/akbp.audit.params"))
        self.assertTrue(lines[3]["error"]["details"]["params_schema"].endswith("#/$defs/akbp.context.params"))
        self.assertTrue(lines[4]["error"]["details"]["params_schema"].endswith("#/$defs/akbp.context.params"))
        for line in lines:
            assert_matches_required_schema(self, line["error"]["details"], schema_def("invalid_params_details"))

    def test_conformance_level_errors_report_method_schema(self):
        request = json.dumps({"id": "bad-conformance-level", "method": "akbp.conformance", "params": {"level": "9"}}) + "\n"
        proc = subprocess.run([sys.executable, str(SERVER)], input=request, text=True, capture_output=True, check=True)
        line = json.loads(proc.stdout)
        self.assertEqual(line["error"]["code"], "invalid_params")
        self.assertIn("level must be one of: 0, 1, 2, 3", line["error"]["details"]["type_errors"])
        self.assertTrue(line["error"]["details"]["params_schema"].endswith("#/$defs/akbp.conformance.params"))
        assert_matches_required_schema(self, line["error"]["details"], schema_def("invalid_params_details"))


if __name__ == "__main__":
    unittest.main()
