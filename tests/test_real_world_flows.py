import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "cli" / "akbp.py"
SERVER = ROOT / "tool-server" / "akbp_tool_server.py"


def run(args, *, input=None, check=True):
    proc = subprocess.run(args, input=input, text=True, capture_output=True)
    if check and proc.returncode != 0:
        raise AssertionError(f"command failed: {args}\nSTDOUT={proc.stdout}\nSTDERR={proc.stderr}")
    return proc


def cli(kb, *args, check=True):
    return run([sys.executable, str(CLI), "--path", str(kb), *args], check=check)


def cli_json(kb, *args):
    return json.loads(cli(kb, *args).stdout)


def server_json(requests):
    payload = "".join(json.dumps(request) + "\n" for request in requests)
    proc = run([sys.executable, str(SERVER)], input=payload)
    return [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]


class RealWorldFlowTest(unittest.TestCase):
    def test_producer_consumer_tool_server_flow_with_redaction_and_review_gates(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            producer = base / "producer-kb"
            consumer = base / "consumer-kb"
            notes = base / "incident notes with spaces.md"
            transcript = base / "session transcript.md"
            bundle_json = base / "bundle.json"
            exchange_jsonl = base / "exchange.jsonl"

            notes.write_text(
                textwrap.dedent(
                    """
                    # Release incident notes
                    Decision: Rollback requires a dry-run plan before production apply.
                    Warning: never persist api_key=sk-live-demo in durable memory.
                    Workflow: cite source evidence for every release-risk claim.
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )
            transcript.write_text(
                textwrap.dedent(
                    """
                    User: continue the release-hardening task.
                    Assistant: Found that rollback needs a dry-run first and every release-risk claim needs cited evidence.
                    Decision: Keep the adapter shutdown path review-gated.
                    Blocker: Need explicit approval before applying remembered session facts.
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )

            cli(producer, "init")
            source = cli_json(
                producer,
                "source",
                "add",
                str(notes),
                "--type",
                "file",
                "--title",
                "Incident api_key=sk-live-demo",
            )
            self.assertEqual(source["title"], "Incident [REDACTED]")
            self.assertNotIn("sk-live-demo", json.dumps(source))

            dry = cli_json(
                producer,
                "ingest",
                str(notes),
                "--type",
                "file",
                "--claim",
                "api_key=sk-live-demo should be redacted before durable apply",
                "--dry-run",
            )
            self.assertTrue(dry["dry_run"])
            self.assertTrue(dry["would_write"])
            self.assertNotIn("sk-live-demo", json.dumps(dry))

            ingest = cli_json(
                producer,
                "ingest",
                str(notes),
                "--type",
                "file",
                "--claim",
                "Rollback requires dry-run before apply",
                "--claim-type",
                "workflow",
                "--entity",
                "release-safety",
            )
            self.assertTrue(ingest["created_claims"])
            self.assertTrue(ingest["source_id"])

            remembered = cli_json(
                producer,
                "remember",
                "Adapter shutdown writes must stay review-gated",
                "--type",
                "decision",
                "--evidence",
                source["id"],
                "--entity",
                "adapter-lifecycle",
            )
            self.assertEqual(remembered["evidence"], [source["id"]])

            cli(producer, "index")
            self.assertTrue(cli_json(producer, "search", "rollback dry-run release-risk", "--limit", "5")["results"])
            self.assertTrue(cli_json(producer, "context", "prepare release rollback plan", "--limit", "5")["items"])
            self.assertEqual(cli_json(producer, "cite", remembered["id"])["claim_id"], remembered["id"])

            start, end_preview, end_blocked = server_json(
                [
                    {
                        "id": "start",
                        "method": "akbp.session.start",
                        "path": str(producer),
                        "params": {"task": "release rollback hardening", "limit": 3},
                    },
                    {
                        "id": "end-preview",
                        "method": "akbp.session.end",
                        "path": str(producer),
                        "dry_run": True,
                        "params": {"transcript": str(transcript), "apply": True},
                    },
                    {
                        "id": "end-blocked",
                        "method": "akbp.session.end",
                        "path": str(producer),
                        "params": {"transcript": str(transcript), "apply": True},
                    },
                ]
            )
            self.assertTrue(start["ok"])
            self.assertTrue(start["result"]["session_id"])
            self.assertTrue(end_preview["ok"])
            self.assertTrue(end_preview["result"]["review_required"])
            self.assertFalse(end_blocked["ok"])
            self.assertEqual(end_blocked["error"]["code"], "approval_required")

            exported = cli_json(producer, "export")
            bundle_json.write_text(json.dumps(exported), encoding="utf-8")
            self.assertTrue(cli_json(producer, "export-check", str(bundle_json), "--fail-on-issues")["ok"])

            cli(consumer, "init")
            exchange_jsonl.write_text(
                "\n".join(json.dumps(item) for item in exported["sources"] + exported["claims"][:2]) + "\n",
                encoding="utf-8",
            )
            import_check = cli_json(consumer, "import-check", str(exchange_jsonl), "--fail-on-rejected")
            self.assertTrue(import_check["ok"])
            self.assertEqual(import_check["rejected"], [])
            self.assertEqual(import_check["review"]["review_status"], "ready")
            self.assertEqual(import_check["review"]["blocking_reasons"], [])
            self.assertTrue(import_check["review"]["ready_for_reviewed_apply"])
            self.assertGreaterEqual(import_check["review"]["source_count"], 1)
            self.assertGreaterEqual(import_check["review"]["claim_count"], 1)
            self.assertEqual(import_check["review"]["claims_without_evidence"], [])
            self.assertEqual(import_check["review"]["claims_without_source_evidence"], [])

            apply_preview = cli_json(consumer, "import-apply", str(exchange_jsonl), "--dry-run")
            self.assertTrue(apply_preview["dry_run"])
            self.assertTrue(apply_preview["would_write"])
            self.assertTrue(apply_preview["review"]["ready_for_reviewed_apply"])
            applied = cli_json(consumer, "import-apply", str(exchange_jsonl), "--approved")
            self.assertGreaterEqual(applied["accepted_count"], 1)
            self.assertEqual(applied["rejected_count"], 0)
            cli(consumer, "index")
            self.assertTrue(cli_json(consumer, "search", "review-gated adapter shutdown", "--limit", "5")["results"])

            bad_path, bad_param, bad_secret = server_json(
                [
                    {"id": "bad-path", "method": "akbp.search", "path": "bad\npath", "params": {"query": "x"}},
                    {
                        "id": "bad-param",
                        "method": "akbp.import_check",
                        "path": str(producer),
                        "params": {"file": "bad\nfile.jsonl"},
                    },
                    {
                        "id": "bad-secret",
                        "method": "akbp.ingest",
                        "path": str(producer),
                        "dry_run": True,
                        "params": {"file": str(notes), "claim": "token=ghp_demo should redact"},
                    },
                ]
            )
            self.assertEqual(bad_path["error"]["code"], "invalid_request")
            self.assertEqual(bad_param["error"]["code"], "invalid_params")
            self.assertTrue(bad_secret["ok"])
            self.assertNotIn("ghp_demo", json.dumps(bad_secret))

    def test_import_review_flags_claims_without_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            kb = base / "kb"
            incoming = base / "incoming.jsonl"

            cli(kb, "init")
            incoming.write_text(
                json.dumps(
                    {
                        "kind": "claim",
                        "id": "claim_uncited_runtime_fact",
                        "text": "Decision: runtime facts need review metadata before apply.",
                        "type": "decision",
                        "status": "working",
                        "confidence": 0.72,
                        "scope": "project",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            import_check = cli_json(kb, "import-check", str(incoming), "--fail-on-rejected")
            self.assertTrue(import_check["ok"])
            self.assertEqual(import_check["rejected_count"], 0)
            self.assertFalse(import_check["review"]["ready_for_reviewed_apply"])
            self.assertEqual(import_check["review"]["review_status"], "blocked")
            self.assertEqual(import_check["review"]["blocking_reasons"], ["claims_without_evidence"])
            self.assertEqual(import_check["review"]["claims_without_evidence"], ["claim_uncited_runtime_fact"])
            self.assertIn("Add source evidence", " ".join(import_check["review"]["next_actions"]))
            apply_preview = json.loads(cli(kb, "import-apply", str(incoming), "--dry-run", check=False).stdout)
            self.assertFalse(apply_preview["ok"])
            self.assertFalse(apply_preview["applied"])
            self.assertTrue(apply_preview["review_required"])
            self.assertEqual(apply_preview["would_write"], {"sources": [], "claims": []})
            self.assertEqual(apply_preview["review"]["claims_without_evidence"], ["claim_uncited_runtime_fact"])
            apply_approved = json.loads(cli(kb, "import-apply", str(incoming), "--approved", check=False).stdout)
            self.assertFalse(apply_approved["ok"])
            self.assertFalse(apply_approved["applied"])
            self.assertEqual(apply_approved["review"]["claims_without_evidence"], ["claim_uncited_runtime_fact"])

    def test_import_review_flags_claims_without_registered_source_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            kb = base / "kb"
            incoming = base / "incoming.jsonl"

            cli(kb, "init")
            incoming.write_text(
                json.dumps(
                    {
                        "kind": "claim",
                        "id": "claim_file_path_only_evidence",
                        "text": "Decision: imported claims should cite registered source ids.",
                        "type": "decision",
                        "status": "working",
                        "confidence": 0.72,
                        "evidence": ["notes/session.md"],
                        "scope": "project",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            import_check = cli_json(kb, "import-check", str(incoming), "--fail-on-rejected")
            self.assertTrue(import_check["ok"])
            self.assertEqual(import_check["rejected_count"], 0)
            self.assertFalse(import_check["review"]["ready_for_reviewed_apply"])
            self.assertEqual(import_check["review"]["review_status"], "blocked")
            self.assertEqual(import_check["review"]["blocking_reasons"], ["claims_without_source_evidence"])
            self.assertEqual(import_check["review"]["claims_without_evidence"], [])
            self.assertEqual(import_check["review"]["claims_without_source_evidence"], ["claim_file_path_only_evidence"])
            self.assertIn("registered source ids", " ".join(import_check["review"]["next_actions"]))
            apply_preview = json.loads(cli(kb, "import-apply", str(incoming), "--dry-run", check=False).stdout)
            self.assertFalse(apply_preview["ok"])
            self.assertFalse(apply_preview["applied"])
            self.assertTrue(apply_preview["review_required"])
            self.assertEqual(apply_preview["would_write"], {"sources": [], "claims": []})
            self.assertEqual(apply_preview["review"]["claims_without_source_evidence"], ["claim_file_path_only_evidence"])


if __name__ == "__main__":
    unittest.main()
