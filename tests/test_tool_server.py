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

    def test_all_server_outputs_use_response_envelope(self):
        requests = "\n".join([
            json.dumps({"id": "caps", "method": "akbp.capabilities"}),
            json.dumps({"id": "status", "method": "akbp.status"}),
            json.dumps({"id": "bad", "method": "akbp.missing"}),
            json.dumps({"method": "akbp.status"}),
            json.dumps({"id": "bad-params", "method": "akbp.search", "params": {"query": 123}}),
            "not-json",
        ]) + "\n"
        proc = subprocess.run([sys.executable, str(SERVER)], input=requests, text=True, capture_output=True, check=True)
        lines = [json.loads(line) for line in proc.stdout.splitlines()]
        self.assertEqual(len(lines), 6)
        for line in lines:
            with self.subTest(response=line):
                assert_response_envelope(self, line)
        self.assertEqual(lines[0]["error"], None)
        self.assertEqual(lines[2]["error"]["code"], "unknown_method")
        self.assertEqual(lines[3]["error"]["code"], "invalid_request")
        self.assertEqual(lines[4]["error"]["code"], "invalid_params")
        self.assertEqual(lines[5]["error"]["code"], "invalid_json")
        assert_matches_required_schema(self, lines[2]["error"]["details"], schema_def("unknown_method_details"))
        assert_matches_required_schema(self, lines[3]["error"]["details"], schema_def("invalid_request_details"))
        assert_matches_required_schema(self, lines[4]["error"]["details"], schema_def("invalid_params_details"))
        assert_matches_required_schema(self, lines[5]["error"]["details"], schema_def("invalid_json_details"))
        self.assertIn("tool-request.schema.json", lines[5]["error"]["details"]["schema"])

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
        for field in ["method", "path", "argv", "apply_instruction"]:
            self.assertIn(field, dry_run["required"])
        ingest_apply = defs["ingest_result"]
        crystallize = defs["crystallize_session_result"]
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
        capabilities = defs["capabilities_result"]
        self.assertFalse(capabilities["additionalProperties"])
        self.assertFalse(capabilities["properties"]["features"]["additionalProperties"])
        self.assertFalse(capabilities["properties"]["methods"]["additionalProperties"]["additionalProperties"])
        self.assertFalse(capabilities["properties"]["examples"]["items"]["additionalProperties"])
        self.assertIn("features", capabilities["required"])
        self.assertIn("methods", capabilities["required"])
        self.assertEqual(capabilities["properties"]["protocol"], {"const": "akbp-jsonl-tool-server"})
        self.assertFalse(defs["context_result"]["additionalProperties"])
        self.assertIn("items", defs["context_result"]["required"])
        self.assertIn("warnings", defs["context_result"]["required"])
        self.assertFalse(defs["search_result"]["additionalProperties"])
        self.assertIn("backend", defs["search_result"]["required"])
        self.assertIn("results", defs["search_result"]["required"])
        self.assertFalse(defs["status_result"]["additionalProperties"])
        self.assertIn("initialized", defs["status_result"]["required"])
        self.assertIn("entrypoint", defs["status_result"]["required"])
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

    def test_installed_server_capabilities_match_reference_server(self):
        request = json.dumps({"id": "caps", "method": "akbp.capabilities"}) + "\n"
        reference = subprocess.run([sys.executable, str(SERVER)], input=request, text=True, capture_output=True, check=True)
        installed = subprocess.run([sys.executable, str(INSTALLED_SERVER)], input=request, text=True, capture_output=True, check=True)
        reference_result = json.loads(reference.stdout)["result"]
        installed_result = json.loads(installed.stdout)["result"]
        self.assertEqual(installed_result["features"], reference_result["features"])
        self.assertEqual(set(installed_result["methods"]), set(reference_result["methods"]))
        self.assertIn("akbp.import_apply", installed_result["methods"])
        self.assertTrue(installed_result["features"]["method_param_schemas"])
        self.assertTrue(installed_result["features"]["approval_required_errors"])

    def test_status_context_and_capabilities_methods(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            run_cli("--path", str(kb), "init")
            run_cli("--path", str(kb), "remember", "AKBP keeps durable claims", "--evidence", "AKBP.md")
            requests = "\n".join([
                json.dumps({"id": "caps", "path": str(kb), "method": "akbp.capabilities"}),
                json.dumps({"id": "1", "path": str(kb), "method": "akbp.status"}),
                json.dumps({"id": "2", "path": str(kb), "method": "akbp.context", "params": {"task": "durable claims"}}),
            ]) + "\n"
            proc = subprocess.run([sys.executable, str(SERVER)], input=requests, text=True, capture_output=True, check=True)
            lines = [json.loads(line) for line in proc.stdout.splitlines()]
            self.assertEqual(lines[0]["id"], "caps")
            self.assertTrue(lines[0]["result"]["features"]["capability_discovery"])
            self.assertTrue(lines[0]["result"]["features"]["write_review_required"])
            self.assertTrue(lines[0]["result"]["features"]["write_apply_requires_approval"])
            self.assertTrue(lines[0]["result"]["features"]["method_param_schemas"])
            self.assertTrue(lines[0]["result"]["features"]["unknown_param_rejection"])
            self.assertTrue(lines[0]["result"]["features"]["required_param_validation"])
            self.assertTrue(lines[0]["result"]["features"]["approval_required_errors"])
            self.assertEqual(lines[0]["result"]["schemas"]["request"].split("/")[-1], "tool-request.schema.json")
            self.assertEqual(lines[0]["result"]["schemas"]["response"].split("/")[-1], "tool-response.schema.json")
            self.assertIn("akbp.remember", lines[0]["result"]["methods"])
            self.assertIn("akbp.ingest", lines[0]["result"]["methods"])
            self.assertIn("akbp.import_check", lines[0]["result"]["methods"])
            self.assertIn("akbp.import_apply", lines[0]["result"]["methods"])
            self.assertIn("akbp.index", lines[0]["result"]["methods"])
            self.assertIn("akbp.search", lines[0]["result"]["methods"])
            self.assertIn("akbp.audit", lines[0]["result"]["methods"])
            self.assertTrue(lines[0]["result"]["methods"]["akbp.remember"]["review_required"])
            self.assertFalse(lines[0]["result"]["methods"]["akbp.query"]["review_required"])
            examples = lines[0]["result"]["examples"]
            crystallize_examples = [item for item in examples if item["method"] == "akbp.crystallize_session"]
            self.assertTrue(crystallize_examples)
            self.assertTrue(crystallize_examples[0]["dry_run"])
            self.assertTrue(crystallize_examples[0]["params"]["apply"])
            for method in ["akbp.status", "akbp.remember", "akbp.ingest", "akbp.import_check", "akbp.import_apply", "akbp.index", "akbp.search", "akbp.audit", "akbp.cite", "akbp.crystallize_session"]:
                self.assertTrue(lines[0]["result"]["methods"][method]["params_schema"].endswith(f"#/$defs/{method}.params"))
            self.assertEqual(lines[1]["id"], "1")
            self.assertTrue(lines[1]["ok"])
            assert_matches_required_schema(self, lines[1]["result"], schema_def("status_result"))
            self.assertEqual(lines[2]["id"], "2")
            assert_matches_required_schema(self, lines[2]["result"], schema_def("context_result"))
            self.assertTrue(lines[2]["result"]["items"])
            assert_matches_required_schema(self, lines[2]["result"]["items"][0], schema_def("context_item"))

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
            approval_schema = schema_def("approval_required_details")
            for dry, rejected in zip(lines[0::2], lines[1::2]):
                with self.subTest(request=dry["id"]):
                    self.assertTrue(dry["ok"])
                    expected_schema = ingest_dry_run_schema if dry["id"] == "dry-akbp.ingest" else dry_run_schema
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

    def test_crystallize_session_method(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            transcript = Path(d) / "session.md"
            transcript.write_text("# Session\n\nDecision: keep agent knowledge portable.\n", encoding="utf-8")
            run_cli("--path", str(kb), "init")
            requests = "\n".join([
                json.dumps({"id": "dry", "path": str(kb), "method": "akbp.crystallize_session", "dry_run": True, "params": {"transcript": str(transcript), "apply": True}}),
                json.dumps({"id": "apply", "path": str(kb), "method": "akbp.crystallize_session", "approved": True, "params": {"transcript": str(transcript), "apply": True}}),
            ]) + "\n"
            proc = subprocess.run([sys.executable, str(SERVER)], input=requests, text=True, capture_output=True, check=True)
            lines = [json.loads(line) for line in proc.stdout.splitlines()]
            self.assertTrue(lines[0]["result"]["dry_run"])
            self.assertIn("--apply", lines[0]["result"]["argv"])
            self.assertTrue(lines[1]["ok"])
            assert_matches_required_schema(self, lines[1]["result"], schema_def("crystallize_session_result"))
            self.assertTrue(lines[1]["result"]["created_claims"])


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

    def test_invalid_params_are_structured_before_cli(self):
        requests = "\n".join([
            json.dumps({"id": "shape", "method": "akbp.search", "params": "not an object"}),
            json.dumps({"id": "unknown", "method": "akbp.search", "params": {"query": "release", "surprise": True}}),
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
        self.assertEqual(lines[2]["error"]["details"]["missing"], ["transcript"])
        self.assertTrue(lines[2]["error"]["details"]["params_schema"].endswith("#/$defs/akbp.crystallize_session.params"))
        self.assertEqual(lines[3]["error"]["code"], "invalid_params")
        self.assertIn("dry_run must be a boolean", lines[3]["error"]["details"]["type_errors"])
        self.assertIn("limit must be an integer", lines[4]["error"]["details"]["type_errors"])
        self.assertIn("apply must be a boolean", lines[5]["error"]["details"]["type_errors"])
        self.assertIn("query must be a string", lines[6]["error"]["details"]["type_errors"])
        self.assertIn("confidence must be a number", lines[7]["error"]["details"]["type_errors"])
        self.assertIn("evidence items must be strings", lines[8]["error"]["details"]["type_errors"])
        self.assertIn("entity items must be strings", lines[9]["error"]["details"]["type_errors"])
        self.assertIn("limit must be between 1 and 100", lines[10]["error"]["details"]["type_errors"])
        self.assertIn("confidence must be between 0 and 1", lines[11]["error"]["details"]["type_errors"])
        self.assertIn("type must be one of:", lines[12]["error"]["details"]["type_errors"][0])
        self.assertIn("warning", lines[12]["error"]["details"]["type_errors"][0])
        self.assertIn("type must be one of:", lines[13]["error"]["details"]["type_errors"][0])
        self.assertIn("transcript", lines[13]["error"]["details"]["type_errors"][0])
        self.assertIn("claim_type must be one of:", lines[14]["error"]["details"]["type_errors"][0])
        for line in lines[3:]:
            assert_matches_required_schema(self, line["error"]["details"], schema_def("invalid_params_details"))


if __name__ == "__main__":
    unittest.main()
