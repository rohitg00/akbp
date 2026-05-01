import json
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
                self.assertTrue(setup.get("sources") or setup.get("proposed_claims"))

    def test_secret_safety_fixture_has_no_real_secret(self):
        path = FIXTURES / "secret-safety" / "scenario.json"
        text = path.read_text(encoding="utf-8")
        self.assertIn("sk-example", text)
        self.assertNotIn("sk-proj-", text)
        self.assertNotIn("xoxb-", text)


if __name__ == "__main__":
    unittest.main()
