import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "cli" / "akbp.py"


def run_cli(*args):
    return subprocess.run([sys.executable, str(CLI), *args], text=True, capture_output=True, check=True)


class ConformanceExampleTest(unittest.TestCase):
    def test_level_zero_example_passes(self):
        out = run_cli("--path", str(ROOT / "examples" / "level-0"), "conformance", "--level", "0")
        data = json.loads(out.stdout)
        self.assertTrue(data["ok"])
        self.assertTrue(data["levels"]["0"]["ok"])

    def test_level_one_example_passes(self):
        out = run_cli("--path", str(ROOT / "examples" / "level-1"), "conformance", "--level", "1")
        data = json.loads(out.stdout)
        self.assertTrue(data["ok"])
        self.assertTrue(data["levels"]["1"]["ok"])

    def test_level_one_example_passes_level_two_retrieval(self):
        out = run_cli("--path", str(ROOT / "examples" / "level-1"), "conformance", "--level", "2")
        data = json.loads(out.stdout)
        self.assertTrue(data["ok"])
        self.assertTrue(data["levels"]["2"]["ok"])

    def test_level_three_example_passes_lifecycle_relations(self):
        out = run_cli("--path", str(ROOT / "examples" / "level-3"), "conformance", "--level", "3")
        data = json.loads(out.stdout)
        self.assertTrue(data["ok"])
        self.assertTrue(data["levels"]["3"]["ok"])

    def test_end_to_end_agent_flow_example_passes(self):
        example = ROOT / "examples" / "end-to-end-agent-flow"
        out = run_cli("--path", str(example), "conformance", "--level", "3")
        data = json.loads(out.stdout)
        self.assertTrue(data["ok"])
        out = run_cli("--path", str(example), "query", "database migrations rollback")
        results = json.loads(out.stdout)["results"]
        self.assertTrue(results)


    def test_obsidian_vault_example_passes_level_two_retrieval(self):
        example = ROOT / "examples" / "obsidian-vault"
        out = run_cli("--path", str(example), "conformance", "--level", "2")
        data = json.loads(out.stdout)
        self.assertTrue(data["ok"])
        self.assertTrue(data["levels"]["2"]["ok"])
        out = run_cli("--path", str(example), "query", "agent memory contract obsidian vault")
        results = json.loads(out.stdout)["results"]
        self.assertTrue(any(result.get("id") == "claim_obsidian_needs_memory_contract" for result in results))

    def test_coding_agent_structured_transcript_crystallizes(self):
        transcript = ROOT / "examples" / "coding-agent" / "structured-session-transcript.md"
        out = run_cli("--path", str(ROOT / "examples" / "level-0"), "crystallize", str(transcript))
        data = json.loads(out.stdout)
        summary = data["summary"]
        self.assertIn("Use the JSONL tool server as the adapter boundary for local coding agents.", summary["decisions"])
        self.assertIn("Prefer dry-run memory writes before applying durable claims.", summary["preferences"])
        self.assertIn("hosted docs cannot use a protocol domain until it serves real schema files.", summary["blockers"])
        self.assertIn("Update docs/AGENT_FLOW.md after changing the session-end workflow.", summary["actions"])
        self.assertIn("Should runtime-specific adapters live in this repo or separate packages?", summary["questions"])
        self.assertIn("adapters/coding-agent-template/session-end.md", summary["files"])
