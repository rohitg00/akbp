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
