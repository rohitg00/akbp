import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "cli" / "akbp.py"

spec = importlib.util.spec_from_file_location("akbp_cli_for_search_tests", CLI)
akbp_cli = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(akbp_cli)


class SearchQuerySanitizerTest(unittest.TestCase):
    def test_fts_query_preserves_safe_terms_around_dangling_operators(self):
        self.assertEqual(akbp_cli.fts_query("JSONL AND"), '"JSONL"')
        self.assertEqual(akbp_cli.fts_query("JSONL OR NOT Python"), '"JSONL"')
        self.assertEqual(akbp_cli.fts_query("JSONL AND NOT Python"), '"JSONL"')

    def test_fts_query_rejects_operator_only_and_punctuation_only_queries(self):
        self.assertEqual(akbp_cli.fts_query("AND OR NOT"), "")
        self.assertEqual(akbp_cli.fts_query("!!! --- ///"), "")
        self.assertEqual(akbp_cli.fts_query("NOT missing"), "")

    def test_fts_query_supports_mixed_operator_prefix_and_phrase_terms(self):
        self.assertEqual(
            akbp_cli.fts_query('JSONL AND tool* OR "session lifecycle"'),
            '"JSONL" AND tool* OR "session lifecycle"',
        )

    def test_fts_query_preserves_dotted_method_names_as_phrases(self):
        self.assertEqual(akbp_cli.fts_query("akbp.session.start"), '"akbp.session.start"')
        self.assertEqual(
            akbp_cli.fts_query("akbp.session.start AND approved:true"),
            '"akbp.session.start" AND "approved" OR "true"',
        )


if __name__ == "__main__":
    unittest.main()
