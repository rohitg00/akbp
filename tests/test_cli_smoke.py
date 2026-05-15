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
    def test_client_config_generates_negotiated_stdio_profile(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            run_cli("--path", str(kb), "init")
            out = run_cli(
                "--path", str(kb),
                "client-config",
                "--name", "stdio-adapter-test",
                "--profile", "reviewed-writes",
                "--command", "python-module",
            )
            config = json.loads(out.stdout)
            self.assertEqual(config["transport"], "stdio-jsonl")
            self.assertEqual(config["server"]["command"], "python3")
            self.assertEqual(config["server"]["args"], ["-m", "akbp_tool_server"])
            self.assertEqual(config["knowledge_base"]["path"], str(kb.resolve()))
            self.assertEqual(config["startup"]["id"], "capabilities-1")
            self.assertEqual(config["startup"]["method"], "akbp.capabilities")
            self.assertEqual(config["startup"]["path"], str(kb.resolve()))
            self.assertEqual(config["startup"]["params"]["client"], "stdio-adapter-test")
            self.assertIn("capability_negotiation", config["startup"]["params"]["requires"])
            self.assertEqual(config["startup"]["params"]["requires_profiles"], ["reviewed_write"])
            self.assertEqual(config["session_start"]["id"], "session-start-1")
            self.assertEqual(config["session_start"]["method"], "akbp.session.start")
            self.assertEqual(config["session_start"]["path"], str(kb.resolve()))
            self.assertEqual(config["response_contract"]["envelope"]["required"], ["id", "ok", "result", "error"])
            self.assertIn("Branch on error.code", config["response_contract"]["error_rules"][0])
            self.assertEqual(config["response_contract"]["schemas"]["response"], "schemas/tool-response.schema.json")
            self.assertEqual(config["health_check"]["id"], "doctor-1")
            self.assertEqual(config["health_check"]["path"], str(kb.resolve()))
            self.assertEqual(config["health_check"]["recommended_profile_field"], "adapter_readiness.recommended_profile")
            self.assertEqual([step["run"] for step in config["verification"]], ["startup", "health_check", "session_start"])
            self.assertTrue(config["verification"][0]["expect"]["result.negotiation.satisfied"])
            self.assertTrue(config["verification"][1]["expect"]["result.adapter_readiness.reviewed_write_ready"])
            self.assertEqual(config["verification"][1]["expect"]["result.summary.errors"], 0)
            self.assertEqual(config["verification"][2]["expect"]["result.context.items"], "array")
            self.assertEqual(config["safety"]["write_policy"], "dry_run_then_approved")
            self.assertEqual(
                config["safety"]["host_trust_boundary"]["hosted_autonomous_tools"],
                "use_read_only_unless_a_separate_human_approval_step_exists",
            )
            self.assertTrue(config["safety"]["require_human_review_surface"])
            self.assertTrue(config["safety"]["never_auto_apply_session_end"])

            caps = subprocess.run(
                [sys.executable, str(SERVER)],
                input=json.dumps(config["startup"]) + "\n",
                text=True,
                capture_output=True,
                check=True,
            )
            negotiated = json.loads(caps.stdout)
            self.assertTrue(negotiated["result"]["negotiation"]["satisfied"])
            self.assertEqual(negotiated["result"]["negotiation"]["supported_profiles"], ["reviewed_write"])

            read_only = json.loads(run_cli("--path", str(kb), "client-config").stdout)
            self.assertEqual(read_only["startup"]["params"]["requires_profiles"], ["read_only"])
            self.assertEqual(read_only["response_contract"]["envelope"]["ok"], "boolean")
            self.assertEqual(read_only["verification"][1]["run"], "health_check")
            self.assertEqual(read_only["safety"]["write_policy"], "no_writes")

    def test_source_verify_uses_cwd_fallback_for_relative_file_sources(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            run_cli("--path", str(kb), "init")
            cwd_file = Path.cwd() / "akbp-cwd-source-smoke.txt"
            try:
                cwd_file.write_text("cwd source", encoding="utf-8")
                source = json.loads(
                    run_cli("--path", str(kb), "source", "add", cwd_file.name, "--type", "file").stdout
                )
                verified = json.loads(
                    run_cli("--path", str(kb), "source", "verify", source["id"], "--fail-on-issue").stdout
                )
                self.assertTrue(verified["ok"])
                self.assertEqual(verified["counts"]["verified"], 1)
            finally:
                cwd_file.unlink(missing_ok=True)


    def test_quickstart_demo_script_passes(self):
        demo_dir = ROOT / "examples" / "quickstart-demo"
        with tempfile.TemporaryDirectory() as tmp:
            kb = Path(tmp) / "demo-kb"
            result = subprocess.run(
                [str(demo_dir / "run.sh"), str(kb)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=True,
            )
            self.assertIn("AKBP quickstart demo passed", result.stdout)
            self.assertTrue((kb / "export.json").is_file())
            self.assertTrue((kb / ".akbp" / "state.db").is_file())

    def test_init_remember_query_lint(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            run_cli("--path", str(kb), "init")
            self.assertTrue((kb / "wiki" / "index.md").exists())
            self.assertTrue((kb / "AKBP.md").exists())
            entrypoint = (kb / "AKBP.md").read_text(encoding="utf-8")
            self.assertIn("## Memory rules", entrypoint)
            self.assertIn("Use `akbp.context` or `akbp.session.start` before planning", entrypoint)
            self.assertIn("Supersede or contradict stale claims instead of silently rewriting history", entrypoint)
            self.assertIn("durable writes require explicit approval", entrypoint)
            card = json.loads((kb / "akbp.json").read_text(encoding="utf-8"))
            self.assertEqual(card["schema_version"], "0.1-draft")
            self.assertIn("claims", card["artifacts"])
            (kb / "README.md").write_text("# Readme\n", encoding="utf-8")

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

            entity = {
                "id": "entity_agentmemory",
                "name": "AgentMemory",
                "type": "tool",
                "aliases": ["hybrid recall"],
                "description": "JSONL observation log for durable agent context",
                "created_at": "2026-05-01T00:00:00Z",
            }
            relation = {
                "id": "relation_agentmemory_references_recall",
                "source": "entity_agentmemory",
                "relation": "references",
                "target": "entity_hybrid_recall",
                "confidence": 0.8,
                "evidence": [source["id"]],
                "created_at": "2026-05-01T00:00:00Z",
            }
            (kb / "graph" / "entities.jsonl").write_text(json.dumps(entity) + "\n", encoding="utf-8")
            (kb / "graph" / "relations.jsonl").write_text(json.dumps(relation) + "\n", encoding="utf-8")
            run_cli("--path", str(kb), "index")

            out = run_cli("--path", str(kb), "search", "AgentMemory")
            searched = json.loads(out.stdout)
            self.assertTrue(any(item["type"] == "entity" and item["id"] == "entity_agentmemory" for item in searched["results"]))

            out = run_cli("--path", str(kb), "search", "Readme")
            searched = json.loads(out.stdout)
            self.assertTrue(any(item["type"] == "source" and item["id"] == source["id"] for item in searched["results"]))

            out = run_cli("--path", str(kb), "search", "references hybrid recall")
            searched = json.loads(out.stdout)
            self.assertTrue(any(item["type"] == "relation" and item["id"] == "relation_agentmemory_references_recall" for item in searched["results"]))

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

            out = run_cli("--path", str(kb), "search", "Bun - migration")
            searched = json.loads(out.stdout)
            self.assertEqual(searched["fts_query"], '"Bun" OR "migration"')
            self.assertTrue(searched["results"])

            out = run_cli("--path", str(kb), "search", "NOT migration")
            searched = json.loads(out.stdout)
            self.assertEqual(searched["backend"], "sqlite_fts5")
            self.assertEqual(searched["fts_query"], "")
            self.assertEqual(searched["results"], [])

            out = run_cli("--path", str(kb), "search", "!!!")
            searched = json.loads(out.stdout)
            self.assertEqual(searched["backend"], "sqlite_fts5")
            self.assertEqual(searched["fts_query"], "")
            self.assertEqual(searched["results"], [])

            out = run_cli("--path", str(kb), "search", "AND OR NOT")
            searched = json.loads(out.stdout)
            self.assertEqual(searched["backend"], "sqlite_fts5")
            self.assertEqual(searched["fts_query"], "")
            self.assertEqual(searched["results"], [])

            out = run_cli("--path", str(kb), "search", "Bun AND")
            searched = json.loads(out.stdout)
            self.assertEqual(searched["backend"], "sqlite_fts5")
            self.assertEqual(searched["fts_query"], '"Bun"')
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
            self.assertEqual(pack["items"][0]["backend"], "sqlite_fts5")
            self.assertIn("citations", pack["items"][0])

            out = run_cli("--path", str(kb), "context", "continue Bun npm migration", "--max-chars", "40")
            budgeted = json.loads(out.stdout)
            self.assertLessEqual(budgeted["budget"]["summary_chars"], 40)
            self.assertGreaterEqual(budgeted["budget"]["truncated_items"], 1)
            self.assertTrue(any("Context budget truncated" in warning for warning in budgeted["warnings"]))

            out = run_cli("--path", str(kb), "export")
            exported = json.loads(out.stdout)
            self.assertTrue(exported["claims"])
            self.assertTrue(exported["sources"])
            self.assertEqual(exported["manifest"]["format"], "akbp-portable-bundle")
            self.assertEqual(exported["manifest"]["counts"]["claims"], len(exported["claims"]))
            self.assertEqual(exported["manifest"]["counts"]["sources"], len(exported["sources"]))
            self.assertTrue(exported["manifest"]["safety"]["excludes_indexes"])
            self.assertEqual(exported["manifest"]["verification"]["hash_algorithm"], "sha256")

            out = run_cli("--path", str(kb), "source", "verify", "--fail-on-issue")
            source_verify = json.loads(out.stdout)
            self.assertTrue(source_verify["ok"])
            self.assertEqual(source_verify["counts"]["verified"], 1)
            out = run_cli("--path", str(kb), "doctor")
            doctor = json.loads(out.stdout)
            self.assertTrue(doctor["ok"])
            self.assertTrue(doctor["ready_for_adapter"])
            self.assertEqual(doctor["adapter_readiness"]["recommended_profile"], "reviewed_write")
            self.assertTrue(doctor["adapter_readiness"]["read_only_ready"])
            self.assertTrue(doctor["adapter_readiness"]["reviewed_write_ready"])
            self.assertEqual(doctor["adapter_readiness"]["blocking_checks"], [])
            self.assertEqual(doctor["summary"]["errors"], 0)
            self.assertEqual(doctor["next_steps"], [])
            (kb / "README.md").write_text("changed", encoding="utf-8")
            changed_verify = json.loads(run_cli("--path", str(kb), "source", "verify").stdout)
            self.assertFalse(changed_verify["ok"])
            self.assertEqual(changed_verify["counts"]["changed"], 1)

            bundle = Path(d) / "bundle.json"
            bundle.write_text(json.dumps(exported), encoding="utf-8")
            checked = json.loads(run_cli("--path", str(kb), "export-check", str(bundle), "--fail-on-issues").stdout)
            self.assertTrue(checked["ok"])
            self.assertEqual(checked["manifest_format"], "akbp-portable-bundle")
            self.assertEqual(checked["counts"]["claims"], len(exported["claims"]))

            bad_bundle = Path(d) / "bad-bundle.json"
            bad = dict(exported)
            bad["manifest"] = dict(exported["manifest"])
            bad["manifest"]["counts"] = dict(exported["manifest"]["counts"])
            bad["manifest"]["counts"]["claims"] = 999
            bad_bundle.write_text(json.dumps(bad), encoding="utf-8")
            bad_check = json.loads(run_cli("--path", str(kb), "export-check", str(bad_bundle)).stdout)
            self.assertFalse(bad_check["ok"])
            self.assertTrue(any(issue["code"] == "count_mismatch" for issue in bad_check["issues"]))

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
            self.assertGreaterEqual(status["counts"]["claims"], 2)
            self.assertGreaterEqual(status["counts"]["audit_events"], 1)
            self.assertTrue(status["claim_summary"]["latest"])

            self.assertIn("working", status["claim_summary"]["by_status"])
            self.assertFalse(status["source_health"]["ok"])
            self.assertEqual(status["source_health"]["counts"]["changed"], 1)
            self.assertTrue(status["index"]["present"])
            self.assertEqual(status["conformance"]["highest_passing_level"], "3")

            out = run_cli("--path", str(kb), "context", "Bun runtime decision")
            drift_pack = json.loads(out.stdout)
            self.assertTrue(any(source["id"] in warning and "changed" in warning for warning in drift_pack["warnings"]))

            out = run_cli("--path", str(kb), "search", "Bun runtime decision")
            drift_search = json.loads(out.stdout)
            self.assertTrue(any(source["id"] in warning and "changed" in warning for warning in drift_search["warnings"]))

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
            search = json.loads(out.stdout)
            self.assertTrue(search["results"])
            self.assertIn("warnings", search)
            out = run_cli("--path", str(kb), "context", "Bun Python stdlib")
            pack = json.loads(out.stdout)
            context_claim_ids = [item["id"] for item in pack["items"] if item["type"] == "claim"]
            self.assertIn(new_claim["id"], context_claim_ids)
            self.assertNotIn(claim["id"], context_claim_ids)
            self.assertTrue(any(claim["id"] in warning for warning in pack["warnings"]))
            out = run_cli("--path", str(kb), "search", "Bun Python stdlib")
            search = json.loads(out.stdout)
            self.assertTrue(any(claim["id"] in warning for warning in search["warnings"]))

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

    def test_doctor_reports_actionable_first_run_gaps(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            out = subprocess.run(
                [sys.executable, str(CLI), "--path", str(kb), "doctor"],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(out.returncode, 1)
            doctor = json.loads(out.stdout)
            self.assertFalse(doctor["ok"])
            self.assertFalse(doctor["ready_for_adapter"])
            self.assertEqual(doctor["adapter_readiness"]["recommended_profile"], "setup_only")
            self.assertFalse(doctor["adapter_readiness"]["read_only_ready"])
            self.assertFalse(doctor["adapter_readiness"]["reviewed_write_ready"])
            self.assertIn("entrypoint", doctor["adapter_readiness"]["blocking_checks"])
            self.assertGreaterEqual(doctor["summary"]["errors"], 1)
            self.assertEqual(doctor["workflow"]["current_stage"], "create_kb")
            self.assertEqual(doctor["workflow"]["stages"][0]["id"], "create_kb")
            self.assertIn("Run: akbp --path <kb> init", doctor["next_steps"])

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

    def test_source_add_redacts_secret_like_title(self):
        with tempfile.TemporaryDirectory() as tmp:
            kb = Path(tmp) / "kb"
            note = Path(tmp) / "note.md"
            note.write_text("# Note\n", encoding="utf-8")
            run_cli("--path", str(kb), "init")
            proc = run_cli(
                "--path",
                str(kb),
                "source",
                "add",
                str(note),
                "--type",
                "file",
                "--title",
                "Incident api_key=sk-live-demo",
            )
            data = json.loads(proc.stdout)
            self.assertEqual(data["title"], "Incident [REDACTED]")
            self.assertNotIn("sk-live-demo", (kb / "raw" / "sources" / "sources.jsonl").read_text(encoding="utf-8"))

    def test_ingest_redacts_secret_like_title(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            note = Path(d) / "note.md"
            note.write_text("# Safe note\n\nDecision: keep titles clean.\n", encoding="utf-8")
            run_cli("--path", str(kb), "init")
            title = "Incident token=sk-example-title-secret"
            result = run_cli("--path", str(kb), "ingest", str(note), "--title", title)
            payload = json.loads(result.stdout)
            self.assertTrue(payload["ok"])
            sources = (kb / "raw" / "sources" / "sources.jsonl").read_text(encoding="utf-8")
            page = (kb / payload["page"]).read_text(encoding="utf-8")
            self.assertNotIn("sk-example-title-secret", sources)
            self.assertNotIn("sk-example-title-secret", page)
            self.assertIn("[REDACTED]", sources)
            self.assertIn("[REDACTED]", page)

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


    def test_import_rejects_unknown_source_evidence_ids(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            export = Path(d) / "dangling-evidence.jsonl"
            export.write_text(json.dumps({
                "kind": "claim",
                "id": "claim_dangling_evidence",
                "text": "Claims imported from JSONL should cite known source records.",
                "type": "workflow",
                "status": "working",
                "confidence": 0.7,
                "evidence": ["source_missing"],
                "scope": "project",
            }) + "\n", encoding="utf-8")
            run_cli("--path", str(kb), "init")

            checked = json.loads(run_cli("--path", str(kb), "import-check", str(export)).stdout)
            self.assertTrue(checked["ok"])
            self.assertEqual(checked["accepted_count"], 0)
            self.assertEqual(checked["rejected_count"], 1)
            self.assertIn("unknown evidence source id", checked["rejected"][0]["reason"])

            proc = subprocess.run([sys.executable, str(CLI), "--path", str(kb), "import-apply", str(export), "--dry-run"], text=True, capture_output=True)
            self.assertEqual(proc.returncode, 1)
            applied = json.loads(proc.stdout)
            self.assertFalse(applied["ok"])
            self.assertEqual(applied["accepted_count"], 0)
            self.assertEqual(applied["rejected_count"], 1)
            self.assertIn("unknown evidence source id", applied["rejected"][0]["reason"])

    def test_import_rejects_non_list_claim_collections(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            export = Path(d) / "bad-claim-lists.jsonl"
            rows = [
                {
                    "kind": "claim",
                    "id": "claim_string_evidence",
                    "text": "Imported claims must keep evidence as a list.",
                    "type": "workflow",
                    "status": "working",
                    "confidence": 0.7,
                    "evidence": "source_not_a_list",
                    "scope": "project",
                },
                {
                    "kind": "claim",
                    "id": "claim_string_entities",
                    "text": "Imported claims must keep entities as a list.",
                    "type": "workflow",
                    "status": "working",
                    "confidence": 0.7,
                    "evidence": [],
                    "entities": "agent",
                    "scope": "project",
                },
            ]
            export.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            run_cli("--path", str(kb), "init")

            proc = subprocess.run([sys.executable, str(CLI), "--path", str(kb), "import-check", str(export), "--fail-on-rejected"], text=True, capture_output=True)
            self.assertEqual(proc.returncode, 1)
            checked = json.loads(proc.stdout)
            self.assertFalse(checked["ok"])
            self.assertEqual(checked["accepted_count"], 0)
            self.assertEqual(checked["rejected_count"], 2)
            reasons = [item["reason"] for item in checked["rejected"]]
            self.assertTrue(any("evidence must be a list" in reason for reason in reasons))
            self.assertTrue(any("entities must be a list of strings" in reason for reason in reasons))

    def test_import_apply_missing_file_returns_result_shape(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            missing = Path(d) / "missing-export.jsonl"
            run_cli("--path", str(kb), "init")
            proc = subprocess.run([sys.executable, str(CLI), "--path", str(kb), "import-apply", str(missing), "--dry-run"], text=True, capture_output=True)
            self.assertEqual(proc.returncode, 1)
            self.assertEqual(proc.stderr, "")
            data = json.loads(proc.stdout)
            self.assertFalse(data["ok"])
            self.assertEqual(data["file"], str(missing.resolve()))
            self.assertTrue(data["dry_run"])
            self.assertFalse(data["applied"])
            self.assertEqual(data["checked"], 0)
            self.assertEqual(data["error_count"], 1)
            self.assertEqual(data["would_write"], {"sources": [], "claims": []})
            self.assertEqual(data["skipped_existing"], {"sources": [], "claims": []})
            self.assertIn("file not found", data["errors"][0]["error"])

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

    def test_import_check_accepts_export_shaped_source_and_claim_objects(self):
        with tempfile.TemporaryDirectory() as tmp:
            kb = Path(tmp) / "kb"
            source = {
                "id": "source_export_shaped",
                "type": "file",
                "locator": "notes.md",
                "title": "Export shaped source",
                "hash": None,
                "immutable": True,
                "scope": "project",
                "created_at": "2026-05-08T00:00:00Z",
                "metadata": {},
            }
            claim = {
                "id": "claim_export_shaped",
                "text": "Export-shaped claim objects can be imported without adding a kind field.",
                "type": "workflow",
                "status": "working",
                "confidence": 0.8,
                "evidence": ["source_export_shaped"],
                "entities": [],
                "supersedes": [],
                "superseded_by": None,
                "scope": "project",
                "created_at": "2026-05-08T00:00:00Z",
                "updated_at": "2026-05-08T00:00:00Z",
                "last_confirmed_at": None,
            }
            exchange = Path(tmp) / "exchange.jsonl"
            exchange.write_text(json.dumps(source) + "\n" + json.dumps(claim) + "\n", encoding="utf-8")
            run_cli("--path", str(kb), "init")
            checked = json.loads(run_cli("--path", str(kb), "import-check", str(exchange), "--fail-on-rejected").stdout)
            self.assertTrue(checked["ok"])
            self.assertEqual(checked["accepted_count"], 2)
            self.assertEqual(checked["rejected"], [])
            self.assertEqual([item["kind"] for item in checked["accepted"]], ["source", "claim"])

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
            self.assertTrue(dry["review_required"])
            self.assertIn("--approved", dry["apply_instruction"])
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

    def test_import_check_and_apply_accept_portable_bundle_json(self):
        with tempfile.TemporaryDirectory() as d:
            producer = Path(d) / "producer"
            consumer = Path(d) / "consumer"
            note = producer / "handoff.md"
            bundle = Path(d) / "bundle.json"

            run_cli("--path", str(producer), "init")
            note.write_text("Decision: portable bundles should import directly after review.\n", encoding="utf-8")
            source = json.loads(run_cli("--path", str(producer), "source", "add", str(note), "--type", "file").stdout)
            run_cli(
                "--path", str(producer),
                "remember",
                "Portable bundles should import directly after review.",
                "--type", "decision",
                "--evidence", source["id"],
            )
            run_cli("--path", str(producer), "export", "--output", str(bundle))

            run_cli("--path", str(consumer), "init")
            checked = json.loads(run_cli("--path", str(consumer), "import-check", str(bundle), "--fail-on-rejected").stdout)
            self.assertTrue(checked["ok"])
            self.assertEqual(checked["accepted_count"], 2)
            self.assertEqual(checked["rejected_count"], 0)

            preview = json.loads(run_cli("--path", str(consumer), "import-apply", str(bundle), "--dry-run").stdout)
            self.assertTrue(preview["ok"])
            self.assertEqual(preview["would_write"]["sources"], [source["id"]])
            self.assertEqual(len(preview["would_write"]["claims"]), 1)

            applied = json.loads(run_cli("--path", str(consumer), "import-apply", str(bundle), "--approved").stdout)
            self.assertTrue(applied["applied"])
            run_cli("--path", str(consumer), "index", "--incremental")
            context = json.loads(run_cli("--path", str(consumer), "context", "portable bundles direct import").stdout)
            self.assertIn("Portable bundles should import directly", json.dumps(context))

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
            self.assertIn(".akbp/audit.log.jsonl", data["would_write"])
            self.assertNotIn("logs/audit.jsonl", data["would_write"])
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
            preview = json.loads(run_cli("--path", str(kb), "crystallize", str(transcript), "--dry-run").stdout)
            self.assertTrue(preview["dry_run"])
            self.assertFalse(preview["apply"])
            self.assertFalse(Path(preview["page"]).exists())

            out = run_cli("--path", str(kb), "crystallize", str(transcript), "--apply")
            data = json.loads(out.stdout)
            self.assertFalse(data["dry_run"])
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

            conflict = subprocess.run(
                [sys.executable, str(CLI), "--path", str(kb), "crystallize", str(transcript), "--apply", "--dry-run"],
                text=True,
                capture_output=True,
            )
            self.assertNotEqual(conflict.returncode, 0)
            self.assertIn("cannot use --apply and --dry-run together", conflict.stderr)


    def test_relative_source_hash_uses_kb_path_first(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb"
            run_cli("--path", str(kb), "init")
            (kb / "notes.md").write_text("source from kb path\n", encoding="utf-8")
            out = run_cli("--path", str(kb), "source", "add", "notes.md", "--type", "file", "--title", "Notes")
            source = json.loads(out.stdout)
            self.assertEqual(len(source["hash"]), 64)

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
