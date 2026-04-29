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
            self.assertTrue((kb / "AKBP.md").exists())
            card = json.loads((kb / "akbp.json").read_text(encoding="utf-8"))
            self.assertEqual(card["schema_version"], "0.1-draft")
            self.assertIn("claims", card["artifacts"])

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

            out = run_cli("--path", str(kb), "query", "Bun npm")
            results = json.loads(out.stdout)["results"]
            self.assertTrue(results)


            out = run_cli("--path", str(kb), "context", "continue Bun npm migration")
            pack = json.loads(out.stdout)
            self.assertEqual(pack["query"], "continue Bun npm migration")
            self.assertTrue(pack["items"])
            self.assertIn("citations", pack["items"][0])

            out = run_cli("--path", str(kb), "audit", "--limit", "10")
            audit = json.loads(out.stdout)
            self.assertGreaterEqual(audit["count"], 1)

            out = run_cli("--path", str(kb), "status")
            status = json.loads(out.stdout)
            self.assertEqual(status["sources"], 1)
            self.assertTrue(status["card"])
            self.assertTrue(status["entrypoint"])

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

            out = run_cli("--path", str(kb), "conformance", "--level", "2")
            conformance = json.loads(out.stdout)
            self.assertTrue(conformance["ok"])
            self.assertTrue(conformance["levels"]["0"]["ok"])
            self.assertTrue(conformance["levels"]["1"]["ok"])
            self.assertTrue(conformance["levels"]["2"]["ok"])

            out = run_cli("--path", str(kb), "lint")
            self.assertTrue(json.loads(out.stdout)["ok"])

    def test_crystallize_apply_creates_session_page_and_claim(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            transcript = Path(d) / "transcript.md"
            transcript.write_text("We decided to use SQLite for local state.\nTODO: add tool-server implementation.\n", encoding="utf-8")

            run_cli("--path", str(kb), "init")
            out = run_cli("--path", str(kb), "crystallize", str(transcript), "--apply")
            data = json.loads(out.stdout)
            self.assertTrue(Path(data["page"]).exists())

            claims = (kb / "claims" / "claims.jsonl").read_text(encoding="utf-8")
            self.assertIn("SQLite", claims)


if __name__ == "__main__":
    unittest.main()
