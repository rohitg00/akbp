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
    def test_status_and_context_methods(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            run_cli("--path", str(kb), "init")
            run_cli("--path", str(kb), "remember", "AKBP keeps durable claims", "--evidence", "AKBP.md")
            requests = "\n".join([
                json.dumps({"id": "1", "path": str(kb), "method": "akbp.status"}),
                json.dumps({"id": "2", "path": str(kb), "method": "akbp.context", "params": {"task": "durable claims"}}),
            ]) + "\n"
            proc = subprocess.run([sys.executable, str(SERVER)], input=requests, text=True, capture_output=True, check=True)
            lines = [json.loads(line) for line in proc.stdout.splitlines()]
            self.assertEqual(lines[0]["id"], "1")
            self.assertTrue(lines[0]["ok"])
            self.assertEqual(lines[1]["id"], "2")
            self.assertTrue(lines[1]["result"]["items"])

    def test_write_methods(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            run_cli("--path", str(kb), "init")
            requests = "\n".join([
                json.dumps({"id": "source", "path": str(kb), "method": "akbp.source.add", "params": {"locator": "AKBP.md", "type": "file", "title": "Entry point"}}),
                json.dumps({"id": "remember", "path": str(kb), "method": "akbp.remember", "params": {"text": "AKBP has a JSONL local tool server", "type": "fact", "evidence": ["AKBP.md"]}}),
            ]) + "\n"
            proc = subprocess.run([sys.executable, str(SERVER)], input=requests, text=True, capture_output=True, check=True)
            lines = [json.loads(line) for line in proc.stdout.splitlines()]
            self.assertTrue(all(line["ok"] for line in lines))
            self.assertEqual(lines[0]["result"]["type"], "file")
            self.assertEqual(lines[1]["result"]["type"], "fact")


if __name__ == "__main__":
    unittest.main()
