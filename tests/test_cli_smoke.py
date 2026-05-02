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

            out = run_cli("--path", str(kb), "index")
            indexed = json.loads(out.stdout)
            self.assertGreaterEqual(indexed["rows"], 1)
            out = run_cli("--path", str(kb), "search", "Bun")
            searched = json.loads(out.stdout)
            self.assertEqual(searched["backend"], "sqlite_fts5")
            self.assertTrue(searched["results"])

            out = run_cli("--path", str(kb), "search", "Bun: npm OR migration")
            searched = json.loads(out.stdout)
            self.assertEqual(searched["fts_query"], '"Bun" OR "npm" OR "migration"')
            self.assertTrue(searched["results"])

            out = run_cli("--path", str(kb), "index", "--incremental")
            indexed_again = json.loads(out.stdout)
            self.assertGreaterEqual(indexed_again["skipped"], 1)
            self.assertTrue(indexed_again["incremental"])

            out = run_cli("--path", str(kb), "context", "continue Bun npm migration")
            pack = json.loads(out.stdout)
            self.assertEqual(pack["query"], "continue Bun npm migration")
            self.assertTrue(pack["items"])
            self.assertIn("citations", pack["items"][0])

            out = run_cli("--path", str(kb), "export")
            exported = json.loads(out.stdout)
            self.assertTrue(exported["claims"])
            self.assertTrue(exported["sources"])

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
            out = run_cli("--path", str(kb), "search", "stdlib")
            self.assertTrue(json.loads(out.stdout)["results"])

            out = run_cli(
                "--path", str(kb),
                "remember",
                "This project should use a packaged binary immediately",
                "--type", "decision",
                "--evidence", source["id"],
            )
            conflicting_claim = json.loads(out.stdout)
            out = run_cli("--path", str(kb), "contradict", new_claim["id"], conflicting_claim["id"], "--evidence", source["id"] )
            relation = json.loads(out.stdout)
            self.assertEqual(relation["relation"], "contradicts")

            out = run_cli("--path", str(kb), "conformance", "--level", "3")
            conformance = json.loads(out.stdout)
            self.assertTrue(conformance["ok"])
            self.assertTrue(conformance["levels"]["0"]["ok"])
            self.assertTrue(conformance["levels"]["1"]["ok"])
            self.assertTrue(conformance["levels"]["2"]["ok"])
            self.assertTrue(conformance["levels"]["3"]["ok"])

            out = run_cli("--path", str(kb), "lint")
            self.assertTrue(json.loads(out.stdout)["ok"])

    def test_ingest_imports_redacted_page_and_optional_claim(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            note = Path(d) / "note.md"
            note.write_text("# Release Note\n\nDecision: ship small batches.\napi_key=sk-example123456789\n", encoding="utf-8")

            run_cli("--path", str(kb), "init")
            out = run_cli(
                "--path", str(kb),
                "ingest", str(note),
                "--title", "Release note",
                "--claim", "The release process uses small batches.",
                "--claim-type", "decision",
            )
            data = json.loads(out.stdout)
            self.assertTrue(data["ok"])
            self.assertTrue(data["redacted"])
            page = kb / data["page"]
            self.assertTrue(page.exists())
            self.assertIn("[REDACTED]", page.read_text(encoding="utf-8"))
            self.assertNotIn("sk-example123456789", page.read_text(encoding="utf-8"))
            claims = [json.loads(line) for line in (kb / "claims" / "claims.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual(claims[0]["evidence"], [data["source_id"]])

    def test_ingest_redacts_optional_claim_text(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            note = Path(d) / "note.md"
            note.write_text("# Incident Note\n\nBlocker: deployment failed.\n", encoding="utf-8")

            run_cli("--path", str(kb), "init")
            out = run_cli(
                "--path", str(kb),
                "ingest", str(note),
                "--claim", "Deployment failed because token=sk-example123456789 was copied into logs.",
                "--claim-type", "warning",
            )
            data = json.loads(out.stdout)
            self.assertTrue(data["ok"])
            self.assertTrue(data["redacted"])
            claims = [json.loads(line) for line in (kb / "claims" / "claims.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertIn("[REDACTED]", claims[0]["text"])
            self.assertNotIn("sk-example123456789", claims[0]["text"])
            self.assertNotIn("token=", claims[0]["text"])


    def test_ingest_dry_run_previews_redacted_writes_without_creating_kb(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            note = Path(d) / "note.md"
            note.write_text("# Import Preview\n\nDecision: preview before write.\napi_key=sk-example123456789\n", encoding="utf-8")

            out = run_cli(
                "--path", str(kb),
                "ingest", str(note),
                "--claim", "Preview import with token=sk-example123456789 before write.",
                "--dry-run",
            )
            data = json.loads(out.stdout)
            self.assertTrue(data["ok"])
            self.assertTrue(data["dry_run"])
            self.assertTrue(data["redacted"])
            self.assertIn("claims/claims.jsonl", data["would_write"])
            self.assertFalse((kb / "raw" / "sources" / "sources.jsonl").exists())
            self.assertFalse((kb / "claims" / "claims.jsonl").exists())
            self.assertFalse((kb / data["page"]).exists())

    def test_crystallize_apply_creates_session_page_and_claim(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            transcript = Path(d) / "transcript.md"
            transcript.write_text("We decided to use SQLite for local state.\nTODO: add tool-server implementation.\n", encoding="utf-8")

            run_cli("--path", str(kb), "init")
            out = run_cli("--path", str(kb), "crystallize", str(transcript), "--apply")
            data = json.loads(out.stdout)
            self.assertTrue(Path(data["page"]).exists())

            claims = [json.loads(line) for line in (kb / "claims" / "claims.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertTrue(any("SQLite" in claim["text"] for claim in claims))
            self.assertTrue(any(claim["type"] == "decision" for claim in claims))
            self.assertTrue(any(claim["type"] == "observation" for claim in claims))
            self.assertTrue(all(claim["evidence"][0].startswith("source_") for claim in claims))

            sources = [json.loads(line) for line in (kb / "raw" / "sources" / "sources.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual(sources[0]["type"], "transcript")

            out = run_cli("--path", str(kb), "crystallize", str(transcript), "--apply")
            rerun = json.loads(out.stdout)
            self.assertTrue(rerun["skipped_claims"])

    def test_crystallize_extracts_structured_session_sections(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            transcript = Path(d) / "structured-session.md"
            transcript.write_text(
                "\n".join([
                    "# Session",
                    "## Decisions",
                    "- Use the JSONL tool server as the adapter boundary.",
                    "## Preferences",
                    "Rohit: Prefer dry-run first writes before apply.",
                    "## Blockers",
                    "Blocker: OPENAI_API_KEY is missing for embeddings.",
                    "## Action Items",
                    "- Update docs/AGENT_FLOW.md and cli/akbp.py.",
                    "## Open Questions",
                    "Question: Should adapters be runtime-specific?",
                    "Files touched: docs/AGENT_FLOW.md, cli/akbp.py",
                ]),
                encoding="utf-8",
            )

            run_cli("--path", str(kb), "init")
            out = run_cli("--path", str(kb), "crystallize", str(transcript))
            data = json.loads(out.stdout)
            summary = data["summary"]
            self.assertIn("Use the JSONL tool server as the adapter boundary.", summary["decisions"])
            self.assertIn("Prefer dry-run first writes before apply.", summary["preferences"])
            self.assertIn("OPENAI_API_KEY is missing for embeddings.", summary["blockers"])
            self.assertIn("Update docs/AGENT_FLOW.md and cli/akbp.py.", summary["actions"])
            self.assertIn("Should adapters be runtime-specific?", summary["questions"])
            self.assertIn("docs/AGENT_FLOW.md", summary["files"])
            self.assertIn("cli/akbp.py", summary["files"])


if __name__ == "__main__":
    unittest.main()
