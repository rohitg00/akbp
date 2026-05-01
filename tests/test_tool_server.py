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
            self.assertIn("akbp.remember", lines[0]["result"]["methods"])
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

    def test_structured_errors(self):
        requests = json.dumps({"id": "bad", "method": "akbp.missing"}) + "\n"
        proc = subprocess.run([sys.executable, str(SERVER)], input=requests, text=True, capture_output=True, check=True)
        line = json.loads(proc.stdout)
        self.assertFalse(line["ok"])
        self.assertEqual(line["error"]["code"], "unknown_method")
        self.assertIn("available_methods", line["error"]["details"])


if __name__ == "__main__":
    unittest.main()
