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
        if spec.get("type") == "string":
            testcase.assertIsInstance(payload[field], str)
            if spec.get("minLength"):
                testcase.assertGreaterEqual(len(payload[field]), spec["minLength"])


class ToolServerTest(unittest.TestCase):

    def test_response_schema_documents_write_review_shapes(self):
        schema = json.loads((ROOT / "schemas" / "tool-response.schema.json").read_text(encoding="utf-8"))
        defs = schema["$defs"]
        approval = defs["approval_required_details"]
        dry_run = defs["dry_run_review_result"]
        self.assertEqual(approval["properties"]["dry_run"], {"const": False})
        self.assertEqual(approval["properties"]["review_required"], {"const": True})
        self.assertIn("apply_instruction", approval["required"])
        self.assertEqual(dry_run["properties"]["dry_run"], {"const": True})
        self.assertEqual(dry_run["properties"]["review_required"], {"const": True})
        self.assertIn("apply_instruction", dry_run["required"])
        details = schema["properties"]["error"]["anyOf"][1]["properties"]["details"]
        self.assertIn({"$ref": "#/$defs/approval_required_details"}, details["anyOf"])

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
            self.assertEqual(lines[0]["result"]["schemas"]["request"].split("/")[-1], "tool-request.schema.json")
            self.assertEqual(lines[0]["result"]["schemas"]["response"].split("/")[-1], "tool-response.schema.json")
            self.assertIn("akbp.remember", lines[0]["result"]["methods"])
            self.assertIn("akbp.ingest", lines[0]["result"]["methods"])
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
            for method in ["akbp.status", "akbp.remember", "akbp.ingest", "akbp.index", "akbp.search", "akbp.audit", "akbp.cite", "akbp.crystallize_session"]:
                self.assertTrue(lines[0]["result"]["methods"][method]["params_schema"].endswith(f"#/$defs/{method}.params"))
            self.assertEqual(lines[1]["id"], "1")
            self.assertTrue(lines[1]["ok"])
            self.assertEqual(lines[2]["id"], "2")
            self.assertTrue(lines[2]["result"]["items"])

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
            approval_schema = schema_def("approval_required_details")
            for dry, rejected in zip(lines[0::2], lines[1::2]):
                with self.subTest(request=dry["id"]):
                    self.assertTrue(dry["ok"])
                    assert_matches_required_schema(self, dry["result"], dry_run_schema)
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
            self.assertTrue(lines[0]["result"]["incremental"])
            self.assertTrue(lines[1]["ok"])
            self.assertEqual(lines[1]["result"]["backend"], "sqlite_fts5")
            self.assertTrue(lines[1]["result"]["results"])

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
        ]) + "\n"
        proc = subprocess.run([sys.executable, str(SERVER)], input=requests, text=True, capture_output=True, check=True)
        lines = [json.loads(line) for line in proc.stdout.splitlines()]
        self.assertEqual(lines[0]["error"]["code"], "invalid_params")
        self.assertEqual(lines[0]["error"]["message"], "params must be an object")
        self.assertEqual(lines[1]["error"]["code"], "invalid_params")
        self.assertEqual(lines[1]["error"]["details"]["unknown"], ["surprise"])
        self.assertIn("query", lines[1]["error"]["details"]["allowed"])
        self.assertTrue(lines[1]["error"]["details"]["params_schema"].endswith("#/$defs/akbp.search.params"))
        self.assertEqual(lines[2]["error"]["code"], "invalid_params")
        self.assertEqual(lines[2]["error"]["details"]["missing"], ["transcript"])
        self.assertTrue(lines[2]["error"]["details"]["params_schema"].endswith("#/$defs/akbp.crystallize_session.params"))
        self.assertEqual(lines[3]["error"]["code"], "invalid_params")
        self.assertIn("dry_run must be a boolean", lines[3]["error"]["details"]["errors"])
        self.assertIn("limit must be an integer", lines[4]["error"]["details"]["errors"])
        self.assertIn("apply must be a boolean", lines[5]["error"]["details"]["errors"])
        self.assertIn("query must be a string", lines[6]["error"]["details"]["errors"])
        self.assertIn("confidence must be a number", lines[7]["error"]["details"]["errors"])


if __name__ == "__main__":
    unittest.main()
