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
            "akbp.doctor.params",
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

    def test_tool_method_enums_match_record_schemas(self):
        claim_schema = json.loads((ROOT / "schemas" / "claim.schema.json").read_text(encoding="utf-8"))
        source_schema = json.loads((ROOT / "schemas" / "source.schema.json").read_text(encoding="utf-8"))
        method_schema = json.loads((ROOT / "schemas" / "tool-methods.schema.json").read_text(encoding="utf-8"))
        defs = method_schema["$defs"]
        claim_types = claim_schema["properties"]["type"]["enum"]
        source_types = source_schema["properties"]["type"]["enum"]
        self.assertEqual(defs["akbp.remember.params"]["properties"]["type"]["enum"], claim_types)
        self.assertEqual(defs["akbp.supersede.params"]["properties"]["type"]["enum"], claim_types)
        self.assertEqual(defs["akbp.ingest.params"]["properties"]["claim_type"]["enum"], claim_types)
        self.assertEqual(defs["akbp.source.add.params"]["properties"]["type"]["enum"], source_types)
        self.assertEqual(defs["akbp.ingest.params"]["properties"]["type"]["enum"], source_types)


    def test_source_intake_example_documents_review_first_flow(self):
        text = (ROOT / "examples" / "source-intake" / "README.md").read_text(encoding="utf-8")
        script = (ROOT / "examples" / "source-intake" / "run.sh").read_text(encoding="utf-8")
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        combined = text + script
        for required in [
            "AKBP source intake example",
            "AKBP source intake example passed",
            "Record source material before making durable claims",
            "source add",
            "crystallize",
            "akbp.ingest",
            "ingest-preview",
            "ingest-blocked",
            "ingest-approved",
            "approval_required",
            "index-approved",
            "akbp.session.start",
            "import-check",
            "import-apply",
            "--dry-run",
            "--approved",
            "secret-like value",
            "unknown `source_...` evidence id",
            "review-gated source intake ok",
            "cited intake context ok",
        ]:
            self.assertIn(required, combined)
        self.assertIn("./examples/source-intake/run.sh", makefile)

    def test_portable_bundle_example_documents_review_flow(self):
        text = (ROOT / "examples" / "portable-bundle" / "README.md").read_text(encoding="utf-8")
        script = (ROOT / "examples" / "portable-bundle" / "run.sh").read_text(encoding="utf-8")
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        for required in [
            "AKBP portable bundle example",
            "AKBP portable bundle example passed",
            "akbp-portable-bundle",
            "excludes_local_state",
            "excludes_indexes",
            "export-check",
            "import-check",
            "import-apply",
            "--dry-run",
            "--approved",
            "secret-like values",
            "context",
        ]:
            self.assertIn(required, text + script)
        self.assertIn("./examples/portable-bundle/run.sh", makefile)

    def test_read_only_adapter_example_documents_allowlist_flow(self):
        text = (ROOT / "examples" / "read-only-adapter" / "README.md").read_text(encoding="utf-8")
        script = (ROOT / "examples" / "read-only-adapter" / "run.sh").read_text(encoding="utf-8")
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        for required in [
            "AKBP read-only adapter example",
            "AKBP read-only adapter example passed",
            "akbp.capabilities",
            "result.profiles.read_only",
            "akbp.session.start",
            "akbp.import_check",
            "akbp.remember",
            "adapter_read_only_block",
            "no read-only write occurred",
        ]:
            self.assertIn(required, text + script)
        self.assertIn("./examples/read-only-adapter/run.sh", makefile)

    def test_session_start_harness_documents_startup_context_gate(self):
        text = (ROOT / "examples" / "session-start-harness" / "README.md").read_text(encoding="utf-8")
        script = (ROOT / "examples" / "session-start-harness" / "run.sh").read_text(encoding="utf-8")
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        quickstart = (ROOT / "docs" / "ADAPTER_AUTHOR_QUICKSTART.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        combined = text + script + quickstart + readme
        for required in [
            "AKBP session-start harness example",
            "AKBP session-start harness example passed",
            "akbp.capabilities",
            "akbp.doctor",
            "akbp.session.start",
            "read_only",
            "startup_context",
            "ready_for_adapter",
            "session_id",
            "citations",
            "first trusted context call",
        ]:
            self.assertIn(required, combined)
        self.assertIn("./examples/session-start-harness/run.sh", makefile)

    def test_docs_define_adapter_output_quality_harness(self):
        benchmark = (ROOT / "docs" / "BENCHMARK.md").read_text(encoding="utf-8")
        quickstart = (ROOT / "docs" / "ADAPTER_AUTHOR_QUICKSTART.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        combined = benchmark + quickstart + readme
        for required in [
            "agent output quality harness",
            "structured prompts",
            "schema-backed JSONL responses",
            "akbp.capabilities",
            "akbp.doctor",
            "akbp.session.start",
            "dry-run write previews",
            "expected_result_schema",
            "expected_result_fields",
            "expected_error_code",
            "review_required",
            "apply_instruction",
        ]:
            self.assertIn(required, combined)

    def test_stdio_client_config_example_documents_negotiated_setup(self):
        text = (ROOT / "examples" / "stdio-client-config" / "README.md").read_text(encoding="utf-8")
        script = (ROOT / "examples" / "stdio-client-config" / "run.sh").read_text(encoding="utf-8")
        cli_readme = (ROOT / "cli" / "README.md").read_text(encoding="utf-8")
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        combined = text + script + cli_readme
        for required in [
            "Stdio client config",
            "AKBP stdio client config example passed",
            "akbp client-config",
            "akbp.capabilities",
            "akbp.doctor",
            "read_only",
            "ready_for_adapter",
            "first_run_sequence",
            "ordered checklist",
            "scope_selection",
            "first-run trust question",
            "repo-local, team-shared, personal-assistant, and migration KB",
            "reviewed_write",
            "akbp.session.start",
            "dry_run",
            "approved:true",
            "result.negotiation.satisfied",
            "hosted or autonomous tool integrations read-only",
            "tool_protocol_bridge",
            "read-only allowlist",
            "blocked write methods",
            "exact reviewed method, path, and params",
        ]:
            self.assertIn(required, combined)
        self.assertIn("./examples/stdio-client-config/run.sh", makefile)

    def test_adoption_preflight_example_documents_first_run_trust_gate(self):
        text = (ROOT / "examples" / "adoption-preflight" / "README.md").read_text(encoding="utf-8")
        script = (ROOT / "examples" / "adoption-preflight" / "run.sh").read_text(encoding="utf-8")
        guide = (ROOT / "docs" / "ADOPTION_DECISION_GUIDE.md").read_text(encoding="utf-8")
        getting_started = (ROOT / "docs" / "GETTING_STARTED.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        combined = text + script + guide + getting_started + readme + changelog
        for required in [
            "AKBP adoption preflight example",
            "AKBP adoption preflight example passed",
            "first-run trust boundary",
            "read-only trust boundary",
            "cited startup context",
            "portable client config",
            "<AKBP_KB_PATH>",
            "akbp.doctor",
            "akbp.session.start",
            "akbp.remember",
            "approval_required",
            "unapproved write rejection",
            "local, cited, reviewable, and portable",
        ]:
            self.assertIn(required, combined)
        self.assertIn("./examples/adoption-preflight/run.sh", makefile)

    def test_tool_protocol_bridge_example_documents_read_only_preflight(self):
        text = (ROOT / "examples" / "tool-protocol-bridge" / "README.md").read_text(encoding="utf-8")
        script = (ROOT / "examples" / "tool-protocol-bridge" / "run.sh").read_text(encoding="utf-8")
        bridge_doc = (ROOT / "docs" / "TOOL_PROTOCOL_BRIDGE.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        combined = text + script + bridge_doc + readme
        for required in [
            "AKBP tool-protocol bridge preflight",
            "AKBP tool-protocol bridge preflight passed",
            "tool_protocol_bridge.forward_tools",
            "tool_protocol_bridge.host_tool_manifest",
            "read_only_allowlist",
            "blocked_write_methods",
            "akbp.capabilities",
            "akbp.doctor",
            "akbp.session.start",
            "akbp.remember",
            "approval_required",
            "read-only bridge startup ok",
            "direct write blocked ok",
        ]:
            self.assertIn(required, combined)
        self.assertIn("./examples/tool-protocol-bridge/run.sh", makefile)
        self.assertIn("examples/tool-protocol-bridge/", readme)

    def test_tool_protocol_bridge_documents_memory_server_adoption_checklist(self):
        bridge_doc = (ROOT / "docs" / "TOOL_PROTOCOL_BRIDGE.md").read_text(encoding="utf-8")
        landscape = (ROOT / "docs" / "PROTOCOL_LANDSCAPE_LEARNINGS.md").read_text(encoding="utf-8")
        combined = bridge_doc + landscape
        for required in [
            "Evaluate memory-server bridges",
            "bridge adoption checklist",
            "Durable knowledge remains in AKBP files",
            "bridge-owned state",
            "Capability freshness",
            "akbp.capabilities",
            "generated `client-config` data",
            "Cited startup context",
            "akbp.session.start",
            "Write boundary",
            "dry-run preview and approval UI",
            "Error handling",
            "approval_required",
            "invalid_params",
            "Portability",
            "export-checkable bundles",
        ]:
            self.assertIn(required, combined)

    def test_github_copilot_adapter_documents_cloud_agent_read_only_boundary(self):
        readme = (ROOT / "adapters" / "github-copilot" / "README.md").read_text(encoding="utf-8")
        instructions = (ROOT / "adapters" / "github-copilot" / "instructions.md").read_text(encoding="utf-8")
        config = json.loads((ROOT / "adapters" / "github-copilot" / "config.example.json").read_text(encoding="utf-8"))
        docs = (ROOT / "docs" / "ADAPTERS.md").read_text(encoding="utf-8")
        combined = readme + instructions + docs
        for required in [
            "Cloud agent tool safety",
            "hosted cloud-agent tool integrations read-only",
            "result.profiles.read_only",
            "separate human approval step",
            "akbp.session.start",
            "blocked_write_methods",
        ]:
            self.assertIn(required, combined + json.dumps(config))
        self.assertEqual(config["akbp"]["tool_server"]["hosted_cloud_agent_default"], "read_only")
        self.assertEqual(config["akbp"]["hosted_cloud_agent"]["requires_profiles"], ["read_only"])
        self.assertIn("akbp.context", config["akbp"]["hosted_cloud_agent"]["allowed_methods"])
        self.assertIn("akbp.import_check", config["akbp"]["hosted_cloud_agent"]["allowed_methods"])
        self.assertIn("akbp.source.verify", config["akbp"]["hosted_cloud_agent"]["allowed_methods"])
        self.assertIn("akbp.session.end", config["akbp"]["hosted_cloud_agent"]["blocked_write_methods"])
        self.assertIn("akbp.crystallize_session", config["akbp"]["hosted_cloud_agent"]["blocked_write_methods"])

    def test_cross_runtime_context_handoff_documents_portability_contract(self):
        text = (ROOT / "docs" / "CROSS_RUNTIME_CONTEXT.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        adapters = (ROOT / "docs" / "ADAPTERS.md").read_text(encoding="utf-8")
        combined = text + readme + adapters
        for required in [
            "Cross-Runtime Context Handoff",
            "Handoff contract",
            "akbp.capabilities",
            "akbp.session.start",
            "akbp.context",
            "dry_run:true",
            "approved:true",
            "approval_required",
            "read_only",
            "export-check",
            "copied chat transcript",
            "docs/CROSS_RUNTIME_CONTEXT.md",
        ]:
            self.assertIn(required, combined)

    def test_session_memory_boundary_documents_promotion_contract(self):
        boundary = (ROOT / "docs" / "SESSION_MEMORY_BOUNDARY.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        agent_flow = (ROOT / "docs" / "AGENT_FLOW.md").read_text(encoding="utf-8")
        quickstart = (ROOT / "docs" / "ADAPTER_AUTHOR_QUICKSTART.md").read_text(encoding="utf-8")
        cross_runtime = (ROOT / "docs" / "CROSS_RUNTIME_CONTEXT.md").read_text(encoding="utf-8")
        combined = boundary + readme + agent_flow + quickstart + cross_runtime
        for required in [
            "Session Memory Boundary",
            "Runtime scratch",
            "Session summary",
            "Durable project knowledge",
            "Rebuildable local state",
            "memory servers",
            "tool-protocol hosts",
            "akbp.session.start",
            "akbp.session.end",
            "dry_run:true",
            "approved:true",
            "review_required",
            "apply_instruction",
            "akbp.index",
            "akbp.supersede",
            "akbp.contradict",
            "docs/SESSION_MEMORY_BOUNDARY.md",
        ]:
            self.assertIn(required, combined)

    def test_cli_readme_documents_search_query_syntax(self):
        text = (ROOT / "cli" / "README.md").read_text(encoding="utf-8")
        for required in [
            "## Search query syntax",
            "SQLite FTS5",
            "rollback AND release",
            "rollback NOT deprecated",
            "\"release checklist\"",
            "deploy*",
            "fts_query",
            "leading standalone `NOT`",
            "empty result set",
        ]:
            self.assertIn(required, text)

    def test_tool_error_handling_example_documents_structured_failures(self):
        text = (ROOT / "examples" / "tool-error-handling" / "README.md").read_text(encoding="utf-8")
        for required in [
            "error.code",
            "Adapter action matrix",
            "Adapter action",
            "Retry policy",
            "User-visible state",
            "invalid_json",
            "invalid_request",
            "unknown_method",
            "invalid_params",
            "approval_required",
            "cli_error",
            "internal_error",
            "dry_run",
            "approved",
            "trusted local policy",
            "method, path, and params match the reviewed request",
        ]:
            self.assertIn(required, text)


    def test_quickstart_demo_documents_public_alpha_path(self):
        readme = (ROOT / "examples" / "quickstart-demo" / "README.md").read_text(encoding="utf-8")
        script = (ROOT / "examples" / "quickstart-demo" / "run.sh").read_text(encoding="utf-8")
        note = (ROOT / "examples" / "quickstart-demo" / "session-note.md").read_text(encoding="utf-8")
        for required in [
            "AKBP quickstart demo",
            "source verify --fail-on-issue",
            "ingest-preview",
            "ingest-blocked",
            "approval_required",
            "ingest-approved",
            "index-approved",
            "supersedes",
            "audit --event supersede",
            "export-check",
            "conformance --level 3",
            "AKBP quickstart demo passed",
            "docs/TROUBLESHOOTING.md",
            "make demo",
        ]:
            self.assertIn(required, readme + script)
        self.assertIn("small, weekly, and evidence-backed", note)

    def test_getting_started_documents_first_run_value(self):
        guide = (ROOT / "docs" / "GETTING_STARTED.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        install = (ROOT / "docs" / "INSTALL.md").read_text(encoding="utf-8")
        for required in [
            "Create a local knowledge base.",
            "Register source material as evidence.",
            "Preview a durable memory write before applying it.",
            "Reject an unapproved write.",
            "Retrieve cited context for a later agent session.",
            "Supersede stale knowledge without deleting history.",
            "Export and check a portable bundle.",
            "make demo",
            "akbp.remember",
            "supersede",
            "dry_run",
            "approval_required",
            "approved",
            "akbp.context",
            "docs/ADAPTER_AUTHOR_QUICKSTART.md",
        ]:
            self.assertIn(required, guide)
        self.assertIn("docs/GETTING_STARTED.md", readme)
        self.assertIn("docs/GETTING_STARTED.md", install)

    def test_getting_started_shows_file_contract_and_trust_boundary(self):
        guide = (ROOT / "docs" / "GETTING_STARTED.md").read_text(encoding="utf-8")
        for required in [
            "## What gets created",
            "`AKBP.md`",
            "`akbp.json`",
            "`raw/sources/sources.jsonl`",
            "`claims/claims.jsonl`",
            "`graph/relations.jsonl`",
            "`.akbp/`",
            "Portable manifest plus artifacts for inspection or import",
            "Use `dry_run:true` and show the preview",
            "Return `approval_required` without durable writes",
            "Repeat the same request with `approved:true`",
            "Use `akbp.context` or `akbp.session.start` and show citations",
            "Supersede or contradict old claims instead of deleting history",
            "bypassing the main AKBP value",
        ]:
            self.assertIn(required, guide)

    def test_adoption_decision_guide_documents_protocol_fit(self):
        guide = (ROOT / "docs" / "ADOPTION_DECISION_GUIDE.md").read_text(encoding="utf-8")
        getting_started = (ROOT / "docs" / "GETTING_STARTED.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        combined = guide + getting_started + readme
        for required in [
            "Adoption decision guide",
            "portable, reviewable knowledge layer",
            "memory server",
            "local context database",
            "Repo-local AKBP knowledge base plus read-only startup context",
            "akbp.session.start",
            "dry_run:true",
            "approved:true",
            "superseded or contradicted",
            "export and import checks",
            "docs/ADOPTION_DECISION_GUIDE.md",
        ]:
            self.assertIn(required, combined)

    def test_makefile_exposes_demo_target(self):
        text = (ROOT / "Makefile").read_text(encoding="utf-8")
        self.assertIn("demo:", text)
        self.assertIn("examples/quickstart-demo/run.sh", text)

    def test_project_memory_rules_template_documents_review_boundary(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        getting_started = (ROOT / "docs" / "GETTING_STARTED.md").read_text(encoding="utf-8")
        guide = (ROOT / "docs" / "TEMPLATES.md").read_text(encoding="utf-8")
        template = (ROOT / "templates" / "project-memory-rules" / "AKBP.md").read_text(encoding="utf-8")
        combined = guide + template
        for required in [
            "templates/project-memory-rules/AKBP.md",
            "what counts as durable project knowledge",
            "dry_run:true",
            "approved:true",
            "review-gated",
            "Never store",
            "superseded or contradicted",
            "akbp doctor",
            "akbp source verify",
            "akbp conformance --level 2",
            "must not create another durable memory format",
        ]:
            self.assertIn(required, combined)
        self.assertIn("templates/project-memory-rules/AKBP.md", readme)
        self.assertIn("docs/TEMPLATES.md", readme)
        self.assertIn("templates/project-memory-rules/AKBP.md", getting_started)

    def test_troubleshooting_covers_common_dx_failures(self):
        text = (ROOT / "docs" / "TROUBLESHOOTING.md").read_text(encoding="utf-8")
        for required in [
            "akbp command is not found",
            "akbp-tool-server",
            "approval_required",
            "source verify",
            "export-check",
            "Search returns no results",
            "make validate",
        ]:
            self.assertIn(required, text)

    def test_markdown_pages_start_with_heading_not_frontmatter(self):
        markdown = [p for p in ROOT.rglob("*.md") if ".git" not in p.parts]
        self.assertGreaterEqual(len(markdown), 10)
        for path in markdown:
            text = path.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("# "), str(path.relative_to(ROOT)))


    def test_public_reference_guard_blocks_external_positioning_terms(self):
        guard = (ROOT / "tests" / "guard_public_refs.py").read_text(encoding="utf-8")
        tokens = [
            "mir" + "age",
            "Mir" + "age",
            "virtual " + "filesystem",
            "Virtual " + "Filesystem",
        ]
        for token in tokens:
            self.assertIn(token, guard)

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

    def test_adapter_session_end_uses_lifecycle_dry_run(self):
        adapters_root = ROOT / "adapters"
        adapters = [path for path in adapters_root.iterdir() if path.is_dir() and any(path.iterdir())]
        for adapter in adapters:
            text = (adapter / "session-end.md").read_text(encoding="utf-8")
            self.assertIn("akbp.session.end", text, str(adapter.relative_to(ROOT)))
            self.assertIn('"dry_run":true', text, str(adapter.relative_to(ROOT)))
            self.assertIn('"apply":true', text, str(adapter.relative_to(ROOT)))

    def test_adapter_readmes_use_session_end_dry_run(self):
        adapters_root = ROOT / "adapters"
        adapters = [path for path in adapters_root.iterdir() if path.is_dir() and any(path.iterdir())]
        for adapter in adapters:
            text = (adapter / "README.md").read_text(encoding="utf-8")
            self.assertIn("akbp.session.end", text, str(adapter.relative_to(ROOT)))
            self.assertIn("dry-run", text, str(adapter.relative_to(ROOT)))


    def test_adapter_author_quickstart_covers_integration_contract(self):
        text = (ROOT / "docs" / "ADAPTER_AUTHOR_QUICKSTART.md").read_text(encoding="utf-8")
        for required in [
            "Generate a read-only client config first",
            "client-config --name my-adapter --profile read-only",
            "client-config --name my-adapter --profile reviewed-writes",
            "akbp.capabilities",
            "result.profile_contracts",
            "akbp.session.start",
            "akbp.context",
            "akbp.search",
            "dry_run",
            "approved:true",
            "akbp.crystallize_session",
            "akbp.source.verify",
            "error.code",
            "make validate",
        ]:
            self.assertIn(required, text)

    def test_readme_documents_low_friction_adapter_setup(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        for required in [
            "Fastest read-only setup",
            "client-config --name my-adapter --profile read-only",
            "Reviewed-write setup",
            "client-config --name my-adapter --profile reviewed-writes",
            "Use read-only first",
            "startup capability request",
            "session-start method",
            "would-write paths",
            "approved:true",
        ]:
            self.assertIn(required, text)

    def test_adapter_review_checklist_covers_runtime_safety(self):
        text = (ROOT / "docs" / "ADAPTER_REVIEW_CHECKLIST.md").read_text(encoding="utf-8")
        for required in [
            "akbp.capabilities",
            "params_schema",
            "akbp.session.start",
            "akbp.context",
            "akbp.search",
            "akbp.cite",
            "dry_run:true",
            "review_required",
            "apply_instruction",
            "approved:true",
            "akbp.import_check",
            "akbp.import_apply",
            "secret-like values",
            "make validate",
        ]:
            self.assertIn(required, text)

    def test_adapter_docs_use_current_validation_and_session_end_flow(self):
        text = (ROOT / "docs" / "ADAPTERS.md").read_text(encoding="utf-8")
        self.assertIn("akbp.session.end", text)
        self.assertIn("dry-run preview before apply", text)
        self.assertIn("Run `make validate`", text)
        self.assertNotIn("Run `make guard`, `make test`, `make smoke`, and `make benchmark`", text)


    def test_obsidian_doc_positions_akbp_as_memory_contract(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        text = (ROOT / "docs" / "OBSIDIAN.md").read_text(encoding="utf-8")
        self.assertIn("docs/OBSIDIAN.md", readme)
        self.assertIn("examples/obsidian-vault/", readme)
        self.assertIn("examples/obsidian-vault/", text)
        for required in [
            "Obsidian is for humans",
            "AKBP is for agents",
            "AKBP does not replace Obsidian",
            "claims/",
            "raw/",
            "akbp.session.start",
            "akbp.session.end",
            "approved:true",
            "review-gated writes",
        ]:
            self.assertIn(required, text)

    def test_tool_contract_documents_write_safety(self):
        text = (ROOT / "docs" / "TOOL_CONTRACT.md").read_text(encoding="utf-8")
        for required in [
            "## Write-mode safety",
            "akbp.capabilities",
            '"dry_run":true',
            "request-level `dry_run:true`",
            "caller-supplied knowledge-base path",
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

    def test_tool_contract_documents_import_rejection_edges(self):
        text = (ROOT / "docs" / "TOOL_CONTRACT.md").read_text(encoding="utf-8")
        for required in [
            "unknown source-evidence rejection",
            "duplicate import-id rejection",
            "scalar collection-field rejection",
            "without raw secret echo",
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
        methods = json.loads((ROOT / "schemas" / "tool-methods.schema.json").read_text(encoding="utf-8"))
        schema_methods = sorted(
            name.removesuffix(".params")
            for name in methods["$defs"]
            if name.startswith("akbp.") and name.endswith(".params")
        )
        self.assertNotIn("akbp.get_context", text)
        self.assertNotIn("### akbp.archive", text)
        methods_block = text.split("Supported JSONL methods:", 1)[1].split("The CLI also has local-only commands", 1)[0]
        listed_methods = [line.strip()[3:-1] for line in methods_block.splitlines() if line.strip().startswith("- `akbp.")]
        self.assertEqual(len(listed_methods), len(set(listed_methods)), listed_methods)
        self.assertEqual(sorted(listed_methods), schema_methods)
        contracts_block = text.split("Supported method contracts include:", 1)[1].split("Every response uses the same envelope:", 1)[0]
        contract_methods = [line.strip()[3:-1] for line in contracts_block.splitlines() if line.strip().startswith("- `akbp.")]
        self.assertEqual(len(contract_methods), len(set(contract_methods)), contract_methods)
        self.assertEqual(sorted(contract_methods), schema_methods)

    def test_agent_flow_starts_writes_with_dry_run(self):
        text = (ROOT / "docs" / "AGENT_FLOW.md").read_text(encoding="utf-8")
        self.assertIn("Start write-capable calls with dry-run", text)
        self.assertIn('"method":"akbp.ingest"', text)
        self.assertIn('"method":"akbp.session.end"', text)
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
        self.assertIn("result.review_required:true", text)
        self.assertIn("result.apply_instruction", text)
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

    def test_adapter_docs_include_quickstart_matrix(self):
        text = (ROOT / "docs" / "ADAPTERS.md").read_text(encoding="utf-8")
        for required in [
            "## Quickstart matrix",
            "Terminal coding agent",
            "Editor coding agent",
            "Local assistant or automation",
            "Repository-backed agent",
            "Custom tool-protocol bridge",
            "akbp.capabilities",
            "akbp.session.start",
            "akbp.session.end",
            "dry_run:true",
            "approved:true",
            "review_required",
            "apply_instruction",
        ]:
            self.assertIn(required, text)

    def test_all_adapter_configs_define_lifecycle_hooks(self):
        adapters_root = ROOT / "adapters"
        adapters = [path for path in adapters_root.iterdir() if path.is_dir() and any(path.iterdir())]
        for adapter in adapters:
            rel = str(adapter.relative_to(ROOT))
            config = json.loads((adapter / "config.example.json").read_text(encoding="utf-8"))
            lifecycle = config.get("akbp", {}).get("lifecycle", {})
            self.assertEqual(lifecycle.get("session_start_method"), "akbp.session.start", rel)
            self.assertEqual(lifecycle.get("session_end_method"), "akbp.session.end", rel)
            self.assertTrue(lifecycle.get("session_end_dry_run_first"), rel)
            self.assertTrue(lifecycle.get("session_end_apply_requires_approved"), rel)

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
                "akbp.session.end",
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
        self.assertIn("akbp.session.start", release_notes)
        self.assertIn("akbp.session.end", release_notes)
        self.assertIn("adapter lifecycle methods", release_notes)
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
            "import apply flow",
            "import apply malformed JSONL",
            "import apply skipped existing records",
            "invalid parameter rejections",
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
        self.assertIn("import apply success/failure/skipped-record flows", changelog)
        self.assertIn("review-gated writes", changelog)
        self.assertIn("approval-gated non-dry-run writes", changelog)
        self.assertIn("schema-backed invalid parameter errors", changelog)
        self.assertIn("bounded array-item count and length", changelog)
        self.assertIn("range", changelog)
        self.assertIn("enum checks", changelog)
        self.assertIn("invalid parameter rejections", changelog)
        self.assertIn("akbp.session.start", changelog)
        self.assertIn("akbp.session.end", changelog)

    def test_architecture_documents_current_reference_contract(self):
        text = (ROOT / "docs" / "ARCHITECTURE.md").read_text(encoding="utf-8")
        for required in [
            "akbp-tool-server JSONL server",
            "claims/claims.jsonl",
            ".akbp/audit.log.jsonl",
            ".akbp/state.db SQLite FTS5 index",
            "akbp.capabilities",
            "akbp.crystallize_session",
            "dry_run:true",
            "approved:true",
            "make validate",
            "Python 3.9, 3.10, 3.11, and 3.12",
        ]:
            self.assertIn(required, text)

    def test_docs_use_current_context_method_name(self):
        for rel in ["docs/ARCHITECTURE.md", "docs/BUILD_PLAN.md", "docs/TOOL_CONTRACT.md"]:
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertNotIn("akbp.get_context", text, rel)
            self.assertIn("akbp.context", text, rel)

    def test_import_apply_docs_include_review_checklist(self):
        cli_readme = (ROOT / "cli" / "README.md").read_text(encoding="utf-8")
        agent_flow = (ROOT / "docs" / "AGENT_FLOW.md").read_text(encoding="utf-8")
        tool_contract = (ROOT / "docs" / "TOOL_CONTRACT.md").read_text(encoding="utf-8")
        for text in [cli_readme, agent_flow, tool_contract]:
            self.assertIn("accepted_count", text)
            self.assertIn("rejected_count", text)
            self.assertIn("error_count", text)
            self.assertIn("would_write.sources", text)
            self.assertIn("would_write.claims", text)
        self.assertIn("--fail-on-rejected", cli_readme)
        self.assertIn("secret-like values", cli_readme)
        self.assertIn("malformed JSONL", agent_flow)
        self.assertIn("approved:true", tool_contract)

    def test_cli_readme_documents_crystallize_preview(self):
        text = (ROOT / "cli" / "README.md").read_text(encoding="utf-8")
        self.assertIn("akbp crystallize transcript.md` previews", text)
        self.assertIn("akbp crystallize transcript.md --apply", text)
        self.assertIn("without writing durable artifacts", text)
        self.assertIn("structured transcript sections", text)
        self.assertIn("Action Items", text)
        self.assertIn("speaker prefixes", text)


    def test_install_smoke_verifies_console_scripts(self):
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        install_doc = (ROOT / "docs" / "INSTALL.md").read_text(encoding="utf-8")
        for required in [
            "PATH=$$TMP/pkg/bin:$$PATH PYTHONPATH=$$TMP/pkg akbp --path",
            "PATH=$$TMP/pkg/bin:$$PATH PYTHONPATH=$$TMP/pkg akbp-tool-server",
        ]:
            self.assertIn(required, makefile)
        for required in [
            'PATH="$TMP/pkg/bin:$PATH" PYTHONPATH="$TMP/pkg" akbp --path',
            'PATH="$TMP/pkg/bin:$PATH" PYTHONPATH="$TMP/pkg" akbp-tool-server',
            "console scripts work",
        ]:
            self.assertIn(required, install_doc)

    def test_validate_target_is_documented_and_used_by_ci(self):
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        install_doc = (ROOT / "docs" / "INSTALL.md").read_text(encoding="utf-8")
        release_doc = (ROOT / "docs" / "RELEASE.md").read_text(encoding="utf-8")
        ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertIn("benchmark-score:", makefile)
        self.assertIn("examples:", makefile)
        self.assertIn("validate: guard test smoke examples benchmark-score benchmark install-smoke", makefile)
        self.assertIn("make validate", readme)
        self.assertIn("make validate", install_doc)
        self.assertIn("make validate", release_doc)
        self.assertIn("installed JSONL tool-server capability", release_doc)
        self.assertIn("make validate", ci)
        self.assertIn("python3 -m akbp_tool_server", makefile)
        self.assertIn("method_param_schemas", makefile)
        self.assertIn("akbp.import_apply", makefile)
        self.assertIn("invalid_params", makefile)
        self.assertIn("limit must be between 1 and 100", makefile)
        self.assertIn("python3 -m akbp_tool_server", install_doc)
        self.assertIn("akbp.import_apply", install_doc)
        self.assertIn("schema-backed `invalid_params`", install_doc)


    def test_readme_has_public_landing_page_quality_sections(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for required in [
            "Agents should not start every session with amnesia.",
            "docs/assets/akbp-product-explainer-banner.png",
            "LLM Wiki v2",
            "stop re-deriving, start compiling",
            "typed claims",
            "review-gated writes",
            "## Why this exists",
            "## What ships today",
            "## See it work",
            "make demo",
            "## The sprint loop for agents",
            "## Tool server contract",
            "## Adapter path",
            "## Architecture",
            "## Validation",
            "## Roadmap to 1.0",
            "It is still alpha",
        ]:
            self.assertIn(required, readme)
        self.assertNotIn("tiny installable reference CLI", readme)
        self.assertNotIn("The narrow MVP", readme)
        banner = ROOT / "docs" / "assets" / "akbp-product-explainer-banner.png"
        self.assertTrue(banner.exists())
        self.assertGreater(banner.stat().st_size, 100_000)

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
        self.assertIn("advertised parameter-schema enforcement features", release_notes)
        self.assertIn("invalid JSON errors", release_notes)
        self.assertIn("do not echo raw input", release_notes)
        self.assertIn("CLI and internal failure details", release_notes)
        self.assertIn("schema-backed invalid JSON", changelog)
        self.assertIn("advertised parameter-schema enforcement features", changelog)
        self.assertIn("CLI and internal failure details", changelog)
        self.assertIn("#/$defs/invalid_json_details", tool_contract)
        self.assertIn("#/$defs/cli_error_details", tool_contract)
        self.assertIn("#/$defs/internal_error_details", tool_contract)
        security_model = (ROOT / "docs" / "SECURITY_MODEL.md").read_text(encoding="utf-8")
        self.assertIn("evidence/entity array validation", tool_contract)
        self.assertIn("at most 64 string items", tool_contract)
        self.assertIn("at most 128 string items", tool_contract)
        self.assertIn("file/path string length caps", security_model)
        self.assertIn("string length caps for import/export file params", security_model)
        self.assertIn("param_array_validation", response_schema)
        self.assertIn("invalid_json_details", response_schema)
        self.assertIn("cli_error_details", response_schema)
        self.assertIn("internal_error_details", response_schema)
        self.assertIn("installed JSONL tool-server smoke coverage", changelog)
        self.assertIn("installed JSONL tool-server entrypoint", release_notes)

    def test_release_notes_list_current_benchmark_coverage(self):
        text = (ROOT / "docs" / "RELEASE_NOTES_DRAFT.md").read_text(encoding="utf-8")
        for required in [
            "import compatibility edges",
            "export bundle compatibility",
            "graph JSONL records",
            "retrieval citation bundle",
            "retrieval ambiguity ranking",
            "retrieval noisy evidence",
            "search index observability",
            "search query compatibility",
            "adapter session operation",
            "adapter write safety",
            "read method schema",
            "unknown method rejection",
            "capability negotiation",
            "write preview crystallize schema",
            "empty FTS query behavior",
            "mixed operator plus prefix FTS search",
            "adapter lifecycle operations",
            "lifecycle method `invalid_params` schema refs",
        ]:
            self.assertIn(required, text)

    def test_tool_contract_search_matches_current_reference_params(self):
        contract = (ROOT / "docs" / "TOOL_CONTRACT.md").read_text(encoding="utf-8")
        methods = json.loads((ROOT / "schemas" / "tool-methods.schema.json").read_text(encoding="utf-8"))
        search_props = methods["$defs"]["akbp.search.params"]["properties"]
        self.assertIn('"query": "string"', contract)
        self.assertIn('"limit": 10', contract)
        self.assertIn("Current backend: `sqlite_fts5`", contract)
        self.assertIn("#/$defs/search_result", contract)
        self.assertIn("leading standalone `NOT`", contract)
        self.assertIn("empty `fts_query`", contract)
        self.assertNotIn('"modes": ["bm25", "vector", "graph"]', contract)
        self.assertNotIn('"scope": "default"', contract)
        self.assertEqual(set(search_props), {"query", "limit"})

    def test_tool_contract_write_params_match_current_reference_params(self):
        contract = (ROOT / "docs" / "TOOL_CONTRACT.md").read_text(encoding="utf-8")
        methods = json.loads((ROOT / "schemas" / "tool-methods.schema.json").read_text(encoding="utf-8"))
        remember_props = methods["$defs"]["akbp.remember.params"]["properties"]
        self.assertIn('"entity": []', contract)
        self.assertIn('"dry_run": false', contract)
        self.assertNotIn('"scope": "private|project|team|public"', contract)
        self.assertIn("caller-supplied knowledge-base path", contract)
        self.assertIn("`akbp.session.start`", contract)
        self.assertIn("`akbp.session.end`", contract)
        self.assertEqual(set(remember_props), {"text", "type", "evidence", "entity", "dry_run"})

    def test_tool_server_approval_example_is_complete(self):
        text = (ROOT / "examples" / "tool-server-approval-flow" / "README.md").read_text(encoding="utf-8")
        script = (ROOT / "examples" / "tool-server-approval-flow" / "run.sh").read_text(encoding="utf-8")
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        self.assertIn("dry_run:true", text)
        self.assertIn("review_required", text)
        self.assertIn("apply_instruction", text)
        self.assertIn("approval_required", text)
        self.assertIn("approved:true", text)
        self.assertIn("claims/claims.jsonl", text)
        self.assertIn("#/$defs/dry_run_review_result", text)
        self.assertIn("#/$defs/approval_required_details", text)
        self.assertIn("schemas/tool-response.schema.json", text)
        for required in [
            "AKBP tool-server approval flow",
            "capabilities ok",
            "reviewed remember flow ok",
            "reviewed import flow ok",
            "AKBP tool-server approval flow passed",
            "akbp.capabilities",
            "akbp.remember",
            "akbp.import_apply",
            "akbp.context",
            "conformance --level 2",
        ]:
            self.assertIn(required, text + script)
        self.assertIn("./examples/tool-server-approval-flow/run.sh", makefile)
        release_notes = (ROOT / "docs" / "RELEASE_NOTES_DRAFT.md").read_text(encoding="utf-8")
        self.assertIn("examples/tool-server-approval-flow/", release_notes)
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("JSONL tool-server approval flow", changelog)

    def test_adapter_lifecycle_example_is_complete(self):
        text = (ROOT / "examples" / "adapter-lifecycle" / "README.md").read_text(encoding="utf-8")
        script = (ROOT / "examples" / "adapter-lifecycle" / "run.sh").read_text(encoding="utf-8")
        transcript = (ROOT / "examples" / "adapter-lifecycle" / "session-summary.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        release_notes = (ROOT / "docs" / "RELEASE_NOTES_DRAFT.md").read_text(encoding="utf-8")
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        for required in [
            "AKBP adapter lifecycle example",
            "AKBP adapter lifecycle example passed",
            "akbp.capabilities",
            "akbp.session.start",
            "akbp.session.end",
            "params_schema",
            "dry_run:true",
            "approved:true",
            "review_required",
            "apply_instruction",
            "approval_required",
            "akbp.index",
            "akbp.context",
            "lifecycle recall ok",
        ]:
            self.assertIn(required, text + script)
        self.assertIn("examples/adapter-lifecycle/session-summary.md", text)
        self.assertIn("Use `akbp.session.start`", transcript)
        self.assertIn("Use `akbp.session.end`", transcript)
        self.assertIn("examples/adapter-lifecycle/", readme)
        self.assertIn("examples/adapter-lifecycle/", release_notes)
        self.assertIn("./examples/adapter-lifecycle/run.sh", makefile)

    def test_jsonl_quickstart_example_is_complete(self):
        text = (ROOT / "examples" / "jsonl-quickstart" / "README.md").read_text(encoding="utf-8")
        script = (ROOT / "examples" / "jsonl-quickstart" / "run.sh").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        quickstart = (ROOT / "docs" / "ADAPTER_AUTHOR_QUICKSTART.md").read_text(encoding="utf-8")
        landscape = (ROOT / "docs" / "PROTOCOL_LANDSCAPE_LEARNINGS.md").read_text(encoding="utf-8")
        release_notes = (ROOT / "docs" / "RELEASE_NOTES_DRAFT.md").read_text(encoding="utf-8")
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        combined = text + script + readme + quickstart + landscape
        for required in [
            "AKBP JSONL quickstart example",
            "AKBP JSONL quickstart example passed",
            "akbp.capabilities",
            "akbp.session.start",
            "akbp.remember",
            "dry_run:true",
            "approval_required",
            "approved:true",
            "akbp.index",
            "akbp.context",
            "akbp.export",
            "portable export ok",
            "cited recall ok",
        ]:
            self.assertIn(required, combined)
        self.assertIn("examples/jsonl-quickstart/", readme)
        self.assertIn("examples/jsonl-quickstart/", quickstart)
        self.assertIn("examples/jsonl-quickstart/", landscape)
        self.assertIn("examples/jsonl-quickstart/", release_notes)
        self.assertIn("JSONL quickstart example", changelog)
        self.assertIn("./examples/jsonl-quickstart/run.sh", makefile)

    def test_git_native_agent_handoff_example_is_complete(self):
        text = (ROOT / "examples" / "git-native-agent-handoff" / "README.md").read_text(encoding="utf-8")
        script = (ROOT / "examples" / "git-native-agent-handoff" / "run.sh").read_text(encoding="utf-8")
        transcript = (ROOT / "examples" / "git-native-agent-handoff" / "session-summary.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        release_notes = (ROOT / "docs" / "RELEASE_NOTES_DRAFT.md").read_text(encoding="utf-8")
        for required in [
            "akbp.capabilities",
            "akbp.session.start",
            "akbp.session.end",
            "dry_run:true",
            "approved:true",
            "akbp.index",
            "Keep repository state in Git",
        ]:
            self.assertIn(required, text)
        self.assertIn("AKBP git-native handoff example passed", script)
        self.assertIn('"method":"akbp.session.start"', script)
        self.assertIn('"method":"akbp.session.end"', script)
        self.assertIn("Use `akbp.session.start`", transcript)
        self.assertIn("Use `akbp.session.end`", transcript)
        self.assertIn("examples/git-native-agent-handoff/", readme)
        self.assertIn("examples/git-native-agent-handoff/", release_notes)

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

    def test_public_launch_checklist_documents_market_readiness_gates(self):
        checklist = (ROOT / "docs" / "PUBLIC_LAUNCH_CHECKLIST.md").read_text(encoding="utf-8")
        release = (ROOT / "docs" / "RELEASE.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("PUBLIC_LAUNCH_CHECKLIST.md", release)
        self.assertIn("PUBLIC_LAUNCH_CHECKLIST.md", readme)
        for text in ["Positioning gate", "Engineering gate", "Security and privacy gate", "Demo gate", "Launch copy guardrails"]:
            self.assertIn(text, checklist)
        for text in ["make validate", "make build", "GitHub CI", "alpha", "avoid comparing AKBP as a full replacement"]:
            self.assertIn(text, checklist)

    def test_security_model_documents_trust_boundaries(self):
        root = ROOT
        security = (root / "SECURITY.md").read_text(encoding="utf-8")
        model = (root / "docs" / "SECURITY_MODEL.md").read_text(encoding="utf-8")
        readme = (root / "README.md").read_text(encoding="utf-8")
        self.assertIn("docs/SECURITY_MODEL.md", security)
        self.assertIn("Security model", readme)
        for text in ["Trust boundaries", "Write safety contract", "Secret-handling expectations", "Adapter requirements"]:
            self.assertIn(text, model)
        for text in ["request-size limits", "path validation", "bounded evidence/entity arrays", "dry-run previews", "explicit approval"]:
            self.assertIn(text, model)

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
