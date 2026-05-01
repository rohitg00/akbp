#!/usr/bin/env python3
"""AKBP benchmark fixture runner.

This runner is intentionally deterministic. It validates benchmark scenario
shape and reports readiness checks that future retrieval engines can reuse.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURES = ROOT / "benchmarks" / "fixtures"


def load_scenarios(fixtures: Path) -> list[tuple[Path, dict[str, Any]]]:
    scenarios: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(fixtures.glob("*/scenario.json")):
        scenarios.append((path, json.loads(path.read_text(encoding="utf-8"))))
    return scenarios


def ids(rows: list[dict[str, Any]]) -> set[str]:
    return {str(row.get("id")) for row in rows if row.get("id")}


def check_scenario(data: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for field in ["id", "task", "setup", "query", "expected"]:
        if field not in data:
            issues.append(f"missing field: {field}")
    setup = data.get("setup", {})
    if not isinstance(setup, dict):
        return [*issues, "setup must be an object"]
    expected = data.get("expected", {})
    if not isinstance(expected, dict):
        return [*issues, "expected must be an object"]

    source_ids = ids(setup.get("sources", []) or [])
    claim_ids = ids(setup.get("claims", []) or [])
    relation_ids = ids(setup.get("relations", []) or [])

    for claim in setup.get("claims", []) or []:
        for evidence in claim.get("evidence", []) or []:
            if evidence not in source_ids:
                issues.append(f"claim {claim.get('id')} cites missing source {evidence}")
        superseded_by = claim.get("superseded_by")
        if superseded_by and superseded_by not in claim_ids:
            issues.append(f"claim {claim.get('id')} superseded_by missing claim {superseded_by}")
        for old_claim in claim.get("supersedes", []) or []:
            if old_claim not in claim_ids:
                issues.append(f"claim {claim.get('id')} supersedes missing claim {old_claim}")

    for relation in setup.get("relations", []) or []:
        if relation.get("source") not in claim_ids:
            issues.append(f"relation {relation.get('id')} has missing source claim")
        if relation.get("target") not in claim_ids:
            issues.append(f"relation {relation.get('id')} has missing target claim")
        for evidence in relation.get("evidence", []) or []:
            if evidence not in source_ids:
                issues.append(f"relation {relation.get('id')} cites missing source {evidence}")

    for required in expected.get("must_retrieve", []) or []:
        if required not in claim_ids:
            issues.append(f"expected must_retrieve missing setup claim {required}")
    for source in expected.get("must_cite", []) or []:
        if source not in source_ids:
            issues.append(f"expected must_cite missing setup source {source}")
    for preserved in expected.get("must_preserve", []) or []:
        if preserved not in claim_ids:
            issues.append(f"expected must_preserve missing setup claim {preserved}")

    if data.get("id") == "secret-safety-001":
        raw = json.dumps(data)
        if "sk-example" not in raw:
            issues.append("secret-safety fixture must use an obvious fake token")
        if "sk-proj-" in raw or "xoxb-" in raw:
            issues.append("secret-safety fixture must not contain realistic secret prefixes")

    # Keep ids useful for report consumers.
    if not source_ids and not setup.get("proposed_claims"):
        issues.append("setup must include sources or proposed_claims")
    if len(relation_ids) != len(setup.get("relations", []) or []):
        issues.append("relations must have unique ids")
    return issues


def run(fixtures: Path) -> dict[str, Any]:
    scenarios = load_scenarios(fixtures)
    results = []
    for path, data in scenarios:
        issues = check_scenario(data)
        results.append({
            "id": data.get("id", path.parent.name),
            "path": str(path.relative_to(ROOT)),
            "ok": not issues,
            "issues": issues,
        })
    return {
        "ok": all(item["ok"] for item in results) and bool(results),
        "count": len(results),
        "fixtures": str(fixtures.relative_to(ROOT) if fixtures.is_relative_to(ROOT) else fixtures),
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate AKBP benchmark fixtures.")
    parser.add_argument("--fixtures", default=str(DEFAULT_FIXTURES), help="Fixture directory containing */scenario.json files.")
    args = parser.parse_args(argv)
    report = run(Path(args.fixtures).resolve())
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
