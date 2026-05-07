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
            run_cli(
                "--path", str(kb),
                "remember",
                "Database migrations use small verified batches",
                "--type", "workflow",
                "--evidence", source["id"],
            )

            out = run_cli("--path", str(kb), "query", "Bun npm")
            results = json.loads(out.stdout)["results"]
            self.assertTrue(results)

            out = run_cli("--path", str(kb), "index")
            indexed = json.loads(out.stdout)
            self.assertGreaterEqual(indexed["rows"], 1)
            self.assertGreaterEqual(len(indexed["indexed_keys"]), 1)
            out = run_cli("--path", str(kb), "search", "Bun")
            searched = json.loads(out.stdout)
            self.assertEqual(searched["backend"], "sqlite_fts5")
            self.assertTrue(searched["results"])

            out = run_cli("--path", str(kb), "search", "Bun: npm OR migration")
            searched = json.loads(out.stdout)
            self.assertEqual(searched["fts_query"], '"Bun" OR "npm" OR "migration"')
            self.assertTrue(searched["results"])

            out = run_cli("--path", str(kb), "search", "Bun AND npm")
            searched = json.loads(out.stdout)
            self.assertEqual(searched["fts_query"], '"Bun" AND "npm"')
            self.assertTrue(any("Bun" in item["snippet"] for item in searched["results"]))

            out = run_cli("--path", str(kb), "search", "Bun NOT migration")
            searched = json.loads(out.stdout)
            self.assertEqual(searched["fts_query"], '"Bun" NOT "migration"')
            self.assertTrue(searched["results"])

            out = run_cli("--path", str(kb), "search", '"small verified" batches')
            searched = json.loads(out.stdout)
            self.assertEqual(searched["fts_query"], '"small verified" OR "batches"')
            self.assertTrue(any("small verified" in item["snippet"] for item in searched["results"]))

            out = run_cli("--path", str(kb), "search", "database/migrations; small_verified!")
            searched = json.loads(out.stdout)
            self.assertEqual(searched["fts_query"], '"database/migrations" OR "small_verified"')
            self.assertTrue(searched["results"])

            out = run_cli("--path", str(kb), "search", "migra*")
            searched = json.loads(out.stdout)
            self.assertEqual(searched["fts_query"], "migra*")
            self.assertTrue(any("migration" in item["snippet"].lower() for item in searched["results"]))

            out = run_cli("--path", str(kb), "search", "Bun AND migra*")
            searched = json.loads(out.stdout)
            self.assertEqual(searched["fts_query"], '"Bun" AND migra*')
            self.assertTrue(searched["results"])

            out = run_cli("--path", str(kb), "index", "--incremental")
            indexed_again = json.loads(out.stdout)
            self.assertGreaterEqual(indexed_again["skipped"], 1)
            self.assertTrue(indexed_again["incremental"])
            self.assertGreaterEqual(len(indexed_again["skipped_keys"]), 1)
            self.assertEqual(indexed_again["removed_keys"], [])

            out = run_cli("--path", str(kb), "context", "continue Bun npm migration")
            pack = json.loads(out.stdout)
            self.assertEqual(pack["query"], "continue Bun npm migration")
            self.assertTrue(pack["items"])
            self.assertIn("citations", pack["items"][0])

            out = run_cli("--path", str(kb), "export")
            exported = json.loads(out.stdout)
            self.assertTrue(exported["claims"])
            self.assertTrue(exported["sources"])
            self.assertEqual(exported["manifest"]["format"], "akbp-portable-bundle")
            self.assertEqual(exported["manifest"]["counts"]["claims"], len(exported["claims"]))
            self.assertEqual(exported["manifest"]["counts"]["sources"], len(exported["sources"]))
            self.assertTrue(exported["manifest"]["safety"]["excludes_indexes"])
            self.assertEqual(exported["manifest"]["verification"]["hash_algorithm"], "sha256")

            out = run_cli("--path", str(kb), "audit", "--limit", "10")
            audit = json.loads(out.stdout)
            self.assertGreaterEqual(audit["count"], 1)
            remember_events = [event for event in audit["events"] if event["event"] == "remember"]
            self.assertTrue(remember_events)
            self.assertEqual(remember_events[-1]["operation"]["actor"], "akbp-cli")
            self.assertEqual(remember_events[-1]["operation"]["mode"], "write")
            self.assertEqual(remember_events[-1]["operation"]["outcome"], "ok")

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


    def test_import_check_rejects_secret_like_jsonl_objects(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            export = Path(d) / "session-export.jsonl"
            rows = [
                {"kind": "claim", "id": "claim_safe", "text": "Deployment failed after a redacted example token appeared."},
                {"kind": "claim", "id": "claim_unsafe", "text": "Deployment failed after token=sk-example123456789 appeared."},
            ]
            export.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

            out = run_cli("--path", str(kb), "import-check", str(export))
            data = json.loads(out.stdout)
            self.assertTrue(data["ok"])
            self.assertEqual(data["checked"], 2)
            self.assertEqual(data["accepted_count"], 1)
            self.assertEqual(data["rejected_count"], 1)
            self.assertEqual(data["error_count"], 0)
            self.assertFalse(data["fail_on_rejected"])
            self.assertEqual([item["id"] for item in data["accepted"]], ["claim_safe"])
            self.assertEqual([item["id"] for item in data["rejected"]], ["claim_unsafe"])
            self.assertNotIn("sk-example123456789", out.stdout)

            strict = subprocess.run([sys.executable, str(CLI), "--path", str(kb), "import-check", str(export), "--fail-on-rejected"], text=True, capture_output=True)
            self.assertEqual(strict.returncode, 1)
            strict_data = json.loads(strict.stdout)
            self.assertFalse(strict_data["ok"])
            self.assertTrue(strict_data["fail_on_rejected"])
            self.assertEqual(strict_data["rejected_count"], 1)
            self.assertNotIn("sk-example123456789", strict.stdout)

    def test_import_apply_failure_shape_includes_review_fields(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            export = Path(d) / "unsafe-export.jsonl"
            export.write_text(
                json.dumps({"kind": "claim", "id": "claim_unsafe", "text": "token=sk-example123456789", "type": "workflow", "status": "working", "confidence": 0.7, "evidence": []}) + "\n",
                encoding="utf-8",
            )
            run_cli("--path", str(kb), "init")
            proc = subprocess.run([sys.executable, str(CLI), "--path", str(kb), "import-apply", str(export), "--dry-run"], text=True, capture_output=True)
            self.assertEqual(proc.returncode, 1)
            data = json.loads(proc.stdout)
            self.assertFalse(data["ok"])
            self.assertFalse(data["applied"])
            self.assertEqual(data["would_write"], {"sources": [], "claims": []})
            self.assertEqual(data["skipped_existing"], {"sources": [], "claims": []})
            self.assertEqual(data["rejected_count"], 1)
            self.assertNotIn("sk-example123456789", proc.stdout)

    def test_import_apply_requires_review_and_writes_accepted_objects(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            export = Path(d) / "safe-export.jsonl"
            rows = [
                {"kind": "source", "id": "source_imported_safe", "type": "transcript", "locator": "imports/safe.md", "title": "Safe import"},
                {"kind": "claim", "id": "claim_imported_safe", "text": "Imported JSONL apply writes accepted claims only.", "type": "workflow", "status": "working", "confidence": 0.7, "evidence": ["source_imported_safe"], "scope": "project"},
            ]
            export.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            run_cli("--path", str(kb), "init")

            dry = json.loads(run_cli("--path", str(kb), "import-apply", str(export), "--dry-run").stdout)
            self.assertTrue(dry["ok"])
            self.assertFalse(dry["applied"])
            self.assertEqual(dry["would_write"]["sources"], ["source_imported_safe"])
            self.assertEqual(dry["would_write"]["claims"], ["claim_imported_safe"])
            self.assertFalse((kb / "claims" / "claims.jsonl").read_text(encoding="utf-8").strip())

            blocked = subprocess.run([sys.executable, str(CLI), "--path", str(kb), "import-apply", str(export)], text=True, capture_output=True)
            self.assertEqual(blocked.returncode, 1)
            blocked_data = json.loads(blocked.stdout)
            self.assertTrue(blocked_data["review_required"])

            applied = json.loads(run_cli("--path", str(kb), "import-apply", str(export), "--approved").stdout)
            self.assertTrue(applied["ok"])
            self.assertTrue(applied["applied"])
            claims = [json.loads(line) for line in (kb / "claims" / "claims.jsonl").read_text(encoding="utf-8").splitlines()]
            sources = [json.loads(line) for line in (kb / "raw" / "sources" / "sources.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertIn("claim_imported_safe", {claim["id"] for claim in claims})
            self.assertIn("source_imported_safe", {source["id"] for source in sources})

            duplicate_dry = json.loads(run_cli("--path", str(kb), "import-apply", str(export), "--dry-run").stdout)
            self.assertEqual(duplicate_dry["would_write"], {"sources": [], "claims": []})
            self.assertEqual(duplicate_dry["skipped_existing"]["sources"], ["source_imported_safe"])
            self.assertEqual(duplicate_dry["skipped_existing"]["claims"], ["claim_imported_safe"])

            duplicate_apply = json.loads(run_cli("--path", str(kb), "import-apply", str(export), "--approved").stdout)
            self.assertTrue(duplicate_apply["ok"])
            self.assertEqual(duplicate_apply["would_write"], {"sources": [], "claims": []})
            claims_after_duplicate = [json.loads(line) for line in (kb / "claims" / "claims.jsonl").read_text(encoding="utf-8").splitlines()]
            sources_after_duplicate = [json.loads(line) for line in (kb / "raw" / "sources" / "sources.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual([claim["id"] for claim in claims_after_duplicate].count("claim_imported_safe"), 1)
            self.assertEqual([source["id"] for source in sources_after_duplicate].count("source_imported_safe"), 1)

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


    def test_tool_server_approval_flow_example_behavior(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            run_cli("--path", str(kb), "init")
            text = "Agents need rollback paths before production changes"
            requests = "\n".join([
                json.dumps({
                    "id": "remember-preview",
                    "method": "akbp.remember",
                    "path": str(kb),
                    "dry_run": True,
                    "params": {"text": text, "type": "workflow", "evidence": ["release-review.md"]},
                }),
                json.dumps({
                    "id": "remember-unapproved",
                    "method": "akbp.remember",
                    "path": str(kb),
                    "params": {"text": text, "type": "workflow", "evidence": ["release-review.md"]},
                }),
                json.dumps({
                    "id": "remember-approved",
                    "method": "akbp.remember",
                    "path": str(kb),
                    "approved": True,
                    "params": {"text": text, "type": "workflow", "evidence": ["release-review.md"]},
                }),
                json.dumps({
                    "id": "index-approved",
                    "method": "akbp.index",
                    "path": str(kb),
                    "approved": True,
                    "params": {"incremental": True},
                }),
                json.dumps({
                    "id": "context",
                    "method": "akbp.context",
                    "path": str(kb),
                    "params": {"task": "prepare production release", "limit": 5},
                }),
            ]) + "\n"
            proc = subprocess.run([sys.executable, str(SERVER)], input=requests, text=True, capture_output=True, check=True, cwd=str(ROOT))
            lines = [json.loads(line) for line in proc.stdout.splitlines()]
            self.assertTrue(lines[0]["ok"])
            self.assertTrue(lines[0]["result"]["dry_run"])
            self.assertTrue(lines[0]["result"]["review_required"])
            self.assertIn("apply_instruction", lines[0]["result"])
            self.assertFalse(lines[1]["ok"])
            self.assertEqual(lines[1]["error"]["code"], "approval_required")
            self.assertTrue(lines[1]["error"]["details"]["review_required"])
            self.assertTrue(lines[2]["ok"])
            self.assertEqual(lines[2]["result"]["type"], "workflow")
            self.assertTrue(lines[3]["ok"])
            self.assertTrue(lines[3]["result"]["incremental"])
            self.assertTrue(lines[4]["ok"])
            self.assertTrue(lines[4]["result"]["items"])
            claims = (kb / "claims" / "claims.jsonl").read_text(encoding="utf-8")
            self.assertEqual(claims.count(text), 1)

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
