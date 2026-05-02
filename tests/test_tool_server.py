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


class ToolServerTest(unittest.TestCase):
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
            self.assertEqual(lines[0]["result"]["schemas"]["request"].split("/")[-1], "tool-request.schema.json")
            self.assertEqual(lines[0]["result"]["schemas"]["response"].split("/")[-1], "tool-response.schema.json")
            self.assertIn("akbp.remember", lines[0]["result"]["methods"])
            self.assertIn("akbp.ingest", lines[0]["result"]["methods"])
            self.assertIn("akbp.index", lines[0]["result"]["methods"])
            self.assertIn("akbp.search", lines[0]["result"]["methods"])
            self.assertIn("akbp.audit", lines[0]["result"]["methods"])
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
                json.dumps({"id": "source", "path": str(kb), "method": "akbp.source.add", "params": {"locator": "AKBP.md", "type": "file", "title": "Entry point"}}),
                json.dumps({"id": "remember", "path": str(kb), "method": "akbp.remember", "params": {"text": "AKBP has a JSONL local tool server", "type": "fact", "evidence": ["AKBP.md"]}}),
            ]) + "\n"
            proc = subprocess.run([sys.executable, str(SERVER)], input=requests, text=True, capture_output=True, check=True)
            lines = [json.loads(line) for line in proc.stdout.splitlines()]
            self.assertTrue(all(line["ok"] for line in lines))
            self.assertTrue(lines[0]["result"]["dry_run"])
            self.assertEqual(lines[1]["result"]["type"], "file")
            self.assertEqual(lines[2]["result"]["type"], "fact")
            claims = (kb / "claims" / "claims.jsonl").read_text()
            self.assertNotIn("AKBP dry run does not write", claims)

    def test_index_and_search_methods(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            run_cli("--path", str(kb), "init")
            run_cli("--path", str(kb), "remember", "SQLite index supports tool server search", "--evidence", "AKBP.md")
            requests = "\n".join([
                json.dumps({"id": "index", "path": str(kb), "method": "akbp.index", "params": {"incremental": True}}),
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
                json.dumps({"id": "apply", "path": str(kb), "method": "akbp.crystallize_session", "params": {"transcript": str(transcript), "apply": True}}),
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
        ]) + "\n"
        proc = subprocess.run([sys.executable, str(SERVER)], input=requests, text=True, capture_output=True, check=True)
        lines = [json.loads(line) for line in proc.stdout.splitlines()]
        self.assertEqual([line["error"]["code"] for line in lines], ["invalid_request"] * 3)
        self.assertIn("tool-request.schema.json", lines[0]["error"]["details"]["schema"])
        self.assertIn("missing required field: id", lines[0]["error"]["details"]["errors"])
        self.assertIn("method must be an akbp.* string", lines[1]["error"]["details"]["errors"])
        self.assertIn("dry_run must be a boolean", lines[2]["error"]["details"]["errors"])

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


if __name__ == "__main__":
    unittest.main()
