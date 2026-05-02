import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "benchmarks" / "fixtures"


class BenchmarkFixtureTest(unittest.TestCase):
    def test_benchmark_scenarios_are_well_formed(self):
        scenarios = sorted(FIXTURES.glob("*/scenario.json"))
        self.assertGreaterEqual(len(scenarios), 4)
        for path in scenarios:
            with self.subTest(path=path):
                data = json.loads(path.read_text(encoding="utf-8"))
                self.assertIn("id", data)
                self.assertIn("task", data)
                self.assertIn("setup", data)
                self.assertIn("query", data)
                self.assertIn("expected", data)
                setup = data["setup"]
                self.assertTrue(setup.get("sources") or setup.get("proposed_claims") or setup.get("import_objects"))

    def test_secret_safety_fixture_has_no_real_secret(self):
        path = FIXTURES / "secret-safety" / "scenario.json"
        text = path.read_text(encoding="utf-8")
        self.assertIn("sk-example", text)
        self.assertNotIn("sk-proj-", text)
        self.assertNotIn("xoxb-", text)

    def test_benchmark_runner_passes(self):
        runner = ROOT / "benchmarks" / "run_benchmarks.py"
        proc = subprocess.run([sys.executable, str(runner), "--akbp"], text=True, capture_output=True, check=True)
        report = json.loads(proc.stdout)
        self.assertTrue(report["ok"])
        self.assertEqual(report["mode"], "akbp-score")
        self.assertGreaterEqual(report["count"], 4)
        self.assertTrue(all("score" in item for item in report["results"]))
        scored = [item for item in report["results"] if "akbp" in item["score"] and not item["score"]["akbp"].get("skipped")]
        self.assertTrue(scored)


if __name__ == "__main__":
    unittest.main()
