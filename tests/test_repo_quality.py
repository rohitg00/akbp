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
        self.assertEqual(response_schema["required"], ["id", "ok", "result", "error"])
        error_schema = response_schema["properties"]["error"]["anyOf"][1]
        self.assertEqual(error_schema["required"], ["code", "message"])
        defs = method_schema["$defs"]
        for name in ["akbp.query.params", "akbp.context.params", "akbp.index.params", "akbp.search.params", "akbp.remember.params", "akbp.source.add.params", "akbp.ingest.params", "akbp.supersede.params", "akbp.contradict.params"]:
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

    def test_tool_contract_documents_write_safety(self):
        text = (ROOT / "docs" / "TOOL_CONTRACT.md").read_text(encoding="utf-8")
        for required in [
            "## Write-mode safety",
            "akbp.capabilities",
            '"dry_run":true',
            "project-local scope",
            "redact secret-like strings",
        ]:
            self.assertIn(required, text)

    def test_release_docs_match_package_version(self):
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        release_doc = (ROOT / "docs" / "RELEASE.md").read_text(encoding="utf-8")
        match = re.search(r'^version = "([^"]+)"', pyproject, re.MULTILINE)
        self.assertIsNotNone(match)
        self.assertIn(f"reference CLI version: `{match.group(1)}`", release_doc)


if __name__ == "__main__":
    unittest.main()
