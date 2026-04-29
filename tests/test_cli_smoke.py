import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "cli" / "akbp.py"


def run_cli(*args):
    return subprocess.run([sys.executable, str(CLI), *args], text=True, capture_output=True, check=True)


class AkbpCliSmokeTest(unittest.TestCase):
    def test_init_remember_query_lint(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            run_cli("--path", str(kb), "init")
            self.assertTrue((kb / "wiki" / "index.md").exists())

            out = run_cli(
                "--path", str(kb),
                "remember",
                "This project uses Bun instead of npm",
                "--type", "decision",
                "--evidence", "README.md",
            )
            claim = json.loads(out.stdout)
            self.assertEqual(claim["type"], "decision")

            out = run_cli("--path", str(kb), "query", "Bun npm")
            results = json.loads(out.stdout)["results"]
            self.assertTrue(results)


            out = run_cli("--path", str(kb), "context", "continue Bun npm migration")
            pack = json.loads(out.stdout)
            self.assertEqual(pack["query"], "continue Bun npm migration")
            self.assertTrue(pack["items"])
            self.assertIn("citations", pack["items"][0])

            out = run_cli("--path", str(kb), "lint")
            self.assertTrue(json.loads(out.stdout)["ok"])

    def test_crystallize_apply_creates_session_page_and_claim(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            transcript = Path(d) / "transcript.md"
            transcript.write_text("We decided to use SQLite for local state.\nTODO: add MCP server.\n", encoding="utf-8")

            run_cli("--path", str(kb), "init")
            out = run_cli("--path", str(kb), "crystallize", str(transcript), "--apply")
            data = json.loads(out.stdout)
            self.assertTrue(Path(data["page"]).exists())

            claims = (kb / "claims" / "claims.jsonl").read_text(encoding="utf-8")
            self.assertIn("SQLite", claims)


if __name__ == "__main__":
    unittest.main()
