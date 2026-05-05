import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RepoQualityTest(unittest.TestCase):
    def test_all_schemas_parse_and_use_resolvable_ids(self):
        schemas = sorted((ROOT / "schemas").glob("*.json"))
        self.assertGreaterEqual(len(schemas), 11)
        for path in schemas:
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertIn("$schema", data)
            self.assertTrue(
                data["$id"].startswith("https://raw.githubusercontent.com/rohitg00/akbp/main/schemas/"),
                data["$id"],
            )
            self.assertNotIn("akbp.dev", data["$id"])

    def test_tool_envelope_schemas_exist(self):
        request_schema = json.loads((ROOT / "schemas" / "tool-request.schema.json").read_text(encoding="utf-8"))
        response_schema = json.loads((ROOT / "schemas" / "tool-response.schema.json").read_text(encoding="utf-8"))
        method_schema = json.loads((ROOT / "schemas" / "tool-methods.schema.json").read_text(encoding="utf-8"))
        self.assertIn("id", request_schema["required"])
        self.assertIn("method", request_schema["required"])
        self.assertIn("dry_run", request_schema["properties"])
        self.assertIn("approved", request_schema["properties"])
        self.assertEqual(response_schema["required"], ["id", "ok", "result", "error"])
        error_schema = response_schema["properties"]["error"]["anyOf"][1]
        self.assertEqual(error_schema["required"], ["code", "message"])
        defs = method_schema["$defs"]
        for name in [
            "akbp.capabilities.params",
            "akbp.status.params",
            "akbp.query.params",
            "akbp.context.params",
            "akbp.index.params",
            "akbp.search.params",
            "akbp.remember.params",
            "akbp.source.add.params",
            "akbp.ingest.params",
            "akbp.import_check.params",
            "akbp.import_apply.params",
            "akbp.supersede.params",
            "akbp.contradict.params",
            "akbp.crystallize_session.params",
            "akbp.conformance.params",
            "akbp.export.params",
            "akbp.audit.params",
            "akbp.cite.params",
        ]:
            self.assertIn(name, defs)

    def test_markdown_pages_start_with_heading_not_frontmatter(self):
        markdown = [p for p in ROOT.rglob("*.md") if ".git" not in p.parts]
        self.assertGreaterEqual(len(markdown), 10)
        for path in markdown:
            text = path.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("# "), str(path.relative_to(ROOT)))

    def test_no_future_schema_domain(self):
        for path in list(ROOT.rglob("*.md")) + list(ROOT.rglob("*.json")):
            if ".git" in path.parts:
                continue
            self.assertNotIn("akbp.dev", path.read_text(encoding="utf-8"), str(path.relative_to(ROOT)))

    def test_adapter_templates_are_complete(self):
        required_files = {
            "README.md",
            "instructions.md",
            "config.example.json",
            "session-start.md",
            "session-end.md",
            "privacy.md",
        }
        adapters_root = ROOT / "adapters"
        adapters = [path for path in adapters_root.iterdir() if path.is_dir() and any(path.iterdir())]
        self.assertGreaterEqual(len(adapters), 3)
        for adapter in adapters:
            missing = sorted(name for name in required_files if not (adapter / name).is_file())
            self.assertEqual(missing, [], str(adapter.relative_to(ROOT)))
            config = json.loads((adapter / "config.example.json").read_text(encoding="utf-8"))
            self.assertIn("adapter", config)
            self.assertIn("akbp", config)

    def test_adapters_reference_agent_flow(self):
        adapters_root = ROOT / "adapters"
        adapters = [path for path in adapters_root.iterdir() if path.is_dir() and any(path.iterdir())]
        for adapter in adapters:
            markdown_text = "\n".join(
                path.read_text(encoding="utf-8")
                for path in sorted(adapter.glob("*.md"))
            )
            self.assertIn("docs/AGENT_FLOW.md", markdown_text, str(adapter.relative_to(ROOT)))

    def test_adapter_session_end_uses_crystallize_dry_run(self):
        adapters_root = ROOT / "adapters"
        adapters = [path for path in adapters_root.iterdir() if path.is_dir() and any(path.iterdir())]
        for adapter in adapters:
            text = (adapter / "session-end.md").read_text(encoding="utf-8")
            self.assertIn("akbp.crystallize_session", text, str(adapter.relative_to(ROOT)))
            self.assertIn('"dry_run":true', text, str(adapter.relative_to(ROOT)))
            self.assertIn('"apply":true', text, str(adapter.relative_to(ROOT)))

    def test_adapter_readmes_use_crystallize_dry_run(self):
        adapters_root = ROOT / "adapters"
        adapters = [path for path in adapters_root.iterdir() if path.is_dir() and any(path.iterdir())]
        for adapter in adapters:
            text = (adapter / "README.md").read_text(encoding="utf-8")
            self.assertIn("akbp.crystallize_session", text, str(adapter.relative_to(ROOT)))
            self.assertIn("dry-run", text, str(adapter.relative_to(ROOT)))

    def test_adapter_docs_use_current_validation_and_crystallize_flow(self):
        text = (ROOT / "docs" / "ADAPTERS.md").read_text(encoding="utf-8")
        self.assertIn("akbp.crystallize_session", text)
        self.assertIn("dry-run preview before apply", text)
        self.assertIn("Run `make validate`", text)
        self.assertNotIn("Run `make guard`, `make test`, `make smoke`, and `make benchmark`", text)

    def test_tool_contract_documents_write_safety(self):
        text = (ROOT / "docs" / "TOOL_CONTRACT.md").read_text(encoding="utf-8")
        for required in [
            "## Write-mode safety",
            "akbp.capabilities",
            '"dry_run":true',
            "request-level `dry_run:true`",
            "project-local scope",
            "redact secret-like strings",
        ]:
            self.assertIn(required, text)

    def test_tool_contract_documents_write_review_response_shapes(self):
        text = (ROOT / "docs" / "TOOL_CONTRACT.md").read_text(encoding="utf-8")
        for required in [
            "#/$defs/dry_run_review_result",
            "#/$defs/approval_required_details",
            "review_required:true",
            "apply_instruction",
            "approved:true",
            "control-flow contracts",
        ]:
            self.assertIn(required, text)

    def test_tool_contract_documents_crystallize_envelope(self):
        text = (ROOT / "docs" / "TOOL_CONTRACT.md").read_text(encoding="utf-8")
        self.assertIn('"method": "akbp.crystallize_session"', text)
        self.assertIn('"dry_run": true', text)
        self.assertIn('"params": {', text)
        self.assertIn('"apply": true', text)

    def test_tool_contract_lists_supported_jsonl_methods(self):
        text = (ROOT / "docs" / "TOOL_CONTRACT.md").read_text(encoding="utf-8")
        self.assertNotIn("akbp.get_context", text)
        self.assertNotIn("### akbp.archive", text)
        for method in [
            "akbp.capabilities",
            "akbp.status",
            "akbp.query",
            "akbp.context",
            "akbp.index",
            "akbp.search",
            "akbp.remember",
            "akbp.conformance",
            "akbp.export",
            "akbp.audit",
            "akbp.cite",
            "akbp.source.add",
            "akbp.ingest",
            "akbp.supersede",
            "akbp.contradict",
            "akbp.crystallize_session",
        ]:
            self.assertIn(method, text)

    def test_agent_flow_starts_writes_with_dry_run(self):
        text = (ROOT / "docs" / "AGENT_FLOW.md").read_text(encoding="utf-8")
        self.assertIn("Start write-capable calls with dry-run", text)
        self.assertIn('"method":"akbp.ingest"', text)
        self.assertIn('"method":"akbp.crystallize_session"', text)
        self.assertIn('"dry_run":true', text)
        self.assertIn('"apply":true', text)
        self.assertIn("After review or approval", text)
        self.assertIn("akbp ingest --dry-run", text)
        self.assertIn("redaction status", text)
        self.assertIn("would-write paths", text)
        self.assertIn("review_required", text)
        self.assertIn("apply_instruction", text)

    def test_adapter_docs_cover_reviewed_jsonl_imports(self):
        adapters_root = ROOT / "adapters"
        adapters = [path for path in adapters_root.iterdir() if path.is_dir() and any(path.iterdir())]
        for adapter in adapters:
            markdown_text = "\n".join(
                path.read_text(encoding="utf-8")
                for path in sorted(adapter.glob("*.md"))
            )
            self.assertIn("akbp.import_check", markdown_text, str(adapter.relative_to(ROOT)))
            self.assertIn("akbp.import_apply", markdown_text, str(adapter.relative_to(ROOT)))
            self.assertIn("approved:true", markdown_text, str(adapter.relative_to(ROOT)))

    def test_tool_server_approval_example_covers_import_apply(self):
        text = (ROOT / "examples" / "tool-server-approval-flow" / "README.md").read_text(encoding="utf-8")
        self.assertIn("akbp.import_check", text)
        self.assertIn("akbp.import_apply", text)
        self.assertIn("result.would_write.sources", text)
        self.assertIn("approved", text)

    def test_adapter_docs_start_ingest_with_dry_run(self):
        for rel in [
            "adapters/coding-agent-template/README.md",
            "adapters/editor-coding-agent/README.md",
            "adapters/terminal-coding-agent/README.md",
            "adapters/coding-agent-template/session-end.md",
            "adapters/openclaw/README.md",
            "adapters/openclaw/session-end.md",
            "adapters/codex/README.md",
            "adapters/codex/session-end.md",
            "adapters/claude-code/README.md",
            "adapters/claude-code/session-end.md",
            "adapters/cursor/README.md",
            "adapters/cursor/session-end.md",
            "adapters/gemini-cli/README.md",
            "adapters/gemini-cli/session-end.md",
        ]:
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertIn("ingest dry-run", text, rel)

    def test_adapter_docs_surface_review_metadata(self):
        for rel in [
            "adapters/coding-agent-template/README.md",
            "adapters/coding-agent-template/instructions.md",
            "adapters/editor-coding-agent/README.md",
            "adapters/terminal-coding-agent/README.md",
            "adapters/example-coding-agent/README.md",
            "adapters/openclaw/README.md",
            "adapters/openclaw/instructions.md",
            "adapters/openclaw/privacy.md",
            "adapters/codex/README.md",
            "adapters/codex/instructions.md",
            "adapters/codex/privacy.md",
            "adapters/claude-code/README.md",
            "adapters/claude-code/instructions.md",
            "adapters/claude-code/privacy.md",
            "adapters/cursor/README.md",
            "adapters/cursor/instructions.md",
            "adapters/cursor/privacy.md",
            "adapters/gemini-cli/README.md",
            "adapters/gemini-cli/instructions.md",
            "adapters/gemini-cli/privacy.md",
            "docs/ADAPTERS.md",
        ]:
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertIn("review_required", text, rel)
            self.assertIn("apply_instruction", text, rel)

    def test_all_adapter_configs_require_approval_gated_writes(self):
        adapters_root = ROOT / "adapters"
        adapters = [path for path in adapters_root.iterdir() if path.is_dir() and any(path.iterdir())]
        for adapter in adapters:
            rel = str(adapter.relative_to(ROOT))
            config = json.loads((adapter / "config.example.json").read_text(encoding="utf-8"))
            policy = config.get("akbp", {}).get("write_policy", {})
            self.assertIs(policy.get("dry_run_first"), True, rel)
            self.assertIs(policy.get("require_review_metadata"), True, rel)
            self.assertIs(policy.get("apply_requires_approved"), True, rel)
            self.assertEqual(policy.get("default_scope"), "project", rel)

    def test_all_adapter_docs_describe_approval_gated_write_flow(self):
        adapters_root = ROOT / "adapters"
        adapters = [path for path in adapters_root.iterdir() if path.is_dir() and any(path.iterdir())]
        for adapter in adapters:
            rel = str(adapter.relative_to(ROOT))
            combined = "\n".join(
                path.read_text(encoding="utf-8")
                for path in sorted(adapter.glob("*.md"))
            )
            for required in [
                "akbp.capabilities",
                "akbp.context",
                "akbp.crystallize_session",
                "dry_run",
                "review_required",
                "apply_instruction",
                "approved:true",
                "ingest dry-run",
                "Do not store",
            ]:
                self.assertIn(required, combined, f"{rel} missing {required}")

    def test_release_docs_match_package_version(self):
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        release_doc = (ROOT / "docs" / "RELEASE.md").read_text(encoding="utf-8")
        release_notes = (ROOT / "docs" / "RELEASE_NOTES_DRAFT.md").read_text(encoding="utf-8")
        match = re.search(r'^version = "([^"]+)"', pyproject, re.MULTILINE)
        self.assertIsNotNone(match)
        self.assertIn(f"reference CLI version: `{match.group(1)}`", release_doc)
        self.assertIn(f"reference CLI version: `{match.group(1)}`", release_notes)
        self.assertIn("adapters/example-coding-agent/", release_notes)
        self.assertIn("akbp.crystallize_session", release_notes)
        self.assertIn("make validate", release_notes)
        self.assertIn("make benchmark-score", release_notes)
        self.assertIn("ingest dry-run preview responses", release_notes)
        self.assertIn("approval-gated non-dry-run writes", release_notes)
        self.assertIn("approved:true", release_notes)
        for fixture in [
            "preference recall",
            "supersession",
            "contradiction",
            "correction resolution",
            "import safety",
            "multi-agent handoff",
            "review-gated writes",
            "secret safety",
            "session crystallization",
        ]:
            self.assertIn(fixture, release_notes)
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("claim-text redaction", changelog)
        self.assertIn("dry-run previews", changelog)
        self.assertIn("import safety", changelog)
        self.assertIn("review-gated writes", changelog)
        self.assertIn("approval-gated non-dry-run writes", changelog)

    def test_docs_use_current_context_method_name(self):
        for rel in ["docs/ARCHITECTURE.md", "docs/BUILD_PLAN.md", "docs/TOOL_CONTRACT.md"]:
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertNotIn("akbp.get_context", text, rel)
            self.assertIn("akbp.context", text, rel)

    def test_cli_readme_documents_crystallize_preview(self):
        text = (ROOT / "cli" / "README.md").read_text(encoding="utf-8")
        self.assertIn("akbp crystallize transcript.md` previews", text)
        self.assertIn("akbp crystallize transcript.md --apply", text)
        self.assertIn("without writing durable artifacts", text)
        self.assertIn("structured transcript sections", text)
        self.assertIn("Action Items", text)
        self.assertIn("speaker prefixes", text)

    def test_validate_target_is_documented_and_used_by_ci(self):
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        install_doc = (ROOT / "docs" / "INSTALL.md").read_text(encoding="utf-8")
        release_doc = (ROOT / "docs" / "RELEASE.md").read_text(encoding="utf-8")
        ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertIn("benchmark-score:", makefile)
        self.assertIn("validate: guard test smoke benchmark-score benchmark install-smoke", makefile)
        self.assertIn("make validate", readme)
        self.assertIn("make validate", install_doc)
        self.assertIn("make validate", release_doc)
        self.assertIn("make validate", ci)

    def test_readme_documents_tool_write_approval_gate(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("dry_run:true", readme)
        self.assertIn("approved:true", readme)
        self.assertIn("approval_required", readme)
        self.assertIn("review-gated", readme)
        self.assertIn("examples/tool-server-approval-flow/", readme)

    def test_release_notes_track_structured_tool_errors(self):
        release_notes = (ROOT / "docs" / "RELEASE_NOTES_DRAFT.md").read_text(encoding="utf-8")
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        tool_contract = (ROOT / "docs" / "TOOL_CONTRACT.md").read_text(encoding="utf-8")
        response_schema = (ROOT / "schemas" / "tool-response.schema.json").read_text(encoding="utf-8")
        self.assertIn("invalid JSON errors", release_notes)
        self.assertIn("do not echo raw input", release_notes)
        self.assertIn("CLI and internal failure details", release_notes)
        self.assertIn("schema-backed invalid JSON", changelog)
        self.assertIn("CLI and internal failure details", changelog)
        self.assertIn("#/$defs/invalid_json_details", tool_contract)
        self.assertIn("#/$defs/cli_error_details", tool_contract)
        self.assertIn("#/$defs/internal_error_details", tool_contract)
        self.assertIn("invalid_json_details", response_schema)
        self.assertIn("cli_error_details", response_schema)
        self.assertIn("internal_error_details", response_schema)

    def test_tool_server_approval_example_is_complete(self):
        text = (ROOT / "examples" / "tool-server-approval-flow" / "README.md").read_text(encoding="utf-8")
        self.assertIn("dry_run:true", text)
        self.assertIn("review_required", text)
        self.assertIn("apply_instruction", text)
        self.assertIn("approval_required", text)
        self.assertIn("approved:true", text)
        self.assertIn("claims/claims.jsonl", text)
        self.assertIn("#/$defs/dry_run_review_result", text)
        self.assertIn("#/$defs/approval_required_details", text)
        self.assertIn("schemas/tool-response.schema.json", text)
        release_notes = (ROOT / "docs" / "RELEASE_NOTES_DRAFT.md").read_text(encoding="utf-8")
        self.assertIn("examples/tool-server-approval-flow/", release_notes)
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("JSONL tool-server approval flow", changelog)

    def test_readme_lists_tracked_adapter_directories(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for adapter in [
            "coding-agent-template/",
            "example-coding-agent/",
            "terminal-coding-agent/",
            "editor-coding-agent/",
            "openclaw/",
            "codex/",
            "claude-code/",
            "cursor/",
            "gemini-cli/",
        ]:
            self.assertIn(adapter, readme)

    def test_release_docs_require_review_gated_writes_and_approval(self):
        text = (ROOT / "docs" / "RELEASE.md").read_text(encoding="utf-8")
        self.assertIn("review_required", text)
        self.assertIn("apply_instruction", text)
        self.assertIn("approved:true", text)
        self.assertIn("approval_required", text)
        self.assertIn("explicit maintainer approval", text)

    def test_readme_and_release_docs_use_current_layout(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        release_doc = (ROOT / "docs" / "RELEASE.md").read_text(encoding="utf-8")
        self.assertIn("benchmarks/", readme)
        self.assertNotIn("  benchmark/", readme)
        self.assertIn("benchmarks/fixtures/", release_doc)
        self.assertIn("dry-run", release_doc)
        self.assertIn("adapters/coding-agent-template/", release_doc)

    def test_source_distribution_manifest_includes_protocol_artifacts(self):
        manifest = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")
        install_doc = (ROOT / "docs" / "INSTALL.md").read_text(encoding="utf-8")
        release_doc = (ROOT / "docs" / "RELEASE.md").read_text(encoding="utf-8")
        for path in ["docs", "spec", "schemas", "examples", "adapters", "benchmarks", "tool-server"]:
            self.assertIn(path, manifest)
        self.assertIn("MANIFEST.in", install_doc)
        self.assertIn("MANIFEST.in", release_doc)


if __name__ == "__main__":
    unittest.main()
