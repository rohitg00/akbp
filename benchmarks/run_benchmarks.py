#!/usr/bin/env python3
"""AKBP benchmark fixture runner.

This runner is intentionally deterministic. It validates benchmark scenario
shape and reports readiness checks that future retrieval engines can reuse.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
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


def words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9_/-]+", text.lower()) if len(w) > 2}


def retrieval_results(data: dict[str, Any]) -> list[dict[str, Any]]:
    query_words = words(str(data.get("query", "")))
    claims = data.get("setup", {}).get("claims", []) or []
    results = []
    for claim in claims:
        claim_words = words(claim.get("text", "")) | set(claim.get("entities", []) or [])
        overlap = sorted(query_words & claim_words)
        score = len(overlap)
        if score or claim.get("id") in set(data.get("expected", {}).get("must_retrieve", []) or []):
            results.append({
                "id": claim.get("id"),
                "score": score,
                "overlap": overlap,
                "evidence": claim.get("evidence", []),
                "status": claim.get("status", "working"),
                "superseded_by": claim.get("superseded_by"),
            })
    results.sort(key=lambda item: (item["score"], item["status"] != "superseded"), reverse=True)
    return results


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def run_cli(kb: Path, *args: str) -> dict[str, Any]:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "cli" / "akbp.py"), "--path", str(kb), *args],
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(proc.stdout) if proc.stdout.strip().startswith(("{", "[")) else {"stdout": proc.stdout}


def scenario_to_kb(data: dict[str, Any], kb: Path) -> None:
    run_cli(kb, "init")
    setup = data.get("setup", {})
    sources = []
    for source in setup.get("sources", []) or []:
        sources.append({
            "id": source["id"],
            "type": source.get("type", "file"),
            "locator": source.get("locator", source["id"]),
            "title": source.get("title"),
            "hash": None,
            "immutable": True,
            "scope": source.get("scope", "project"),
            "created_at": source.get("created_at", "2026-01-01T00:00:00Z"),
            "metadata": source.get("metadata", {}),
        })
    claims = []
    for claim in setup.get("claims", []) or []:
        claims.append({
            "id": claim["id"],
            "text": claim["text"],
            "type": claim.get("type", "observation"),
            "status": claim.get("status", "working"),
            "confidence": claim.get("confidence", 0.5),
            "evidence": claim.get("evidence", []),
            "entities": claim.get("entities", []),
            "supersedes": claim.get("supersedes", []),
            "superseded_by": claim.get("superseded_by"),
            "scope": claim.get("scope", "project"),
            "created_at": claim.get("created_at", "2026-01-01T00:00:00Z"),
            "updated_at": claim.get("updated_at", "2026-01-01T00:00:00Z"),
            "last_confirmed_at": claim.get("last_confirmed_at"),
        })
    relations = []
    for relation in setup.get("relations", []) or []:
        relations.append({
            "id": relation["id"],
            "source": relation["source"],
            "target": relation["target"],
            "relation": relation.get("relation", "related_to"),
            "evidence": relation.get("evidence", []),
            "created_at": relation.get("created_at", "2026-01-01T00:00:00Z"),
        })
    write_jsonl(kb / "raw" / "sources" / "sources.jsonl", sources)
    write_jsonl(kb / "claims" / "claims.jsonl", claims)
    write_jsonl(kb / "graph" / "relations.jsonl", relations)


def score_real_akbp(data: dict[str, Any]) -> dict[str, Any]:
    if not data.get("setup", {}).get("claims"):
        return {"ok": True, "skipped": "scenario has no stored claims"}
    with tempfile.TemporaryDirectory() as d:
        kb = Path(d) / "kb"
        scenario_to_kb(data, kb)
        query = run_cli(kb, "query", data.get("query", ""), "--limit", "20")
        context = run_cli(kb, "context", data.get("query", ""), "--limit", "20")
    expected = data.get("expected", {})
    query_ids = {item.get("id") for item in query.get("results", [])}
    context_ids = {item.get("id") for item in context.get("items", [])}
    checks = []
    for claim_id in expected.get("must_retrieve", []) or []:
        checks.append({
            "name": "akbp_query_or_context_must_retrieve",
            "ok": claim_id in query_ids or claim_id in context_ids,
            "details": claim_id,
        })
    return {
        "ok": all(check["ok"] for check in checks),
        "query_result_ids": sorted(x for x in query_ids if x),
        "context_item_ids": sorted(x for x in context_ids if x),
        "checks": checks,
    }


def score_scenario(data: dict[str, Any], *, real_akbp: bool = False) -> dict[str, Any]:
    expected = data.get("expected", {})
    setup = data.get("setup", {})
    claims = setup.get("claims", []) or []
    relations = setup.get("relations", []) or []
    retrieved = retrieval_results(data)
    retrieved_ids = {item["id"] for item in retrieved}
    citation_ids = {evidence for item in retrieved for evidence in item.get("evidence", [])}
    claim_by_id = {claim.get("id"): claim for claim in claims}

    checks: list[dict[str, Any]] = []

    def add(name: str, ok: bool, details: Any = None) -> None:
        checks.append({"name": name, "ok": bool(ok), "details": details})

    for claim_id in expected.get("must_retrieve", []) or []:
        add("must_retrieve", claim_id in retrieved_ids, claim_id)
    for source_id in expected.get("must_cite", []) or []:
        add("must_cite", source_id in citation_ids, source_id)
    for claim_id in expected.get("must_preserve", []) or []:
        add("must_preserve", claim_id in claim_by_id, claim_id)
    for claim_id in expected.get("must_not_answer_from", []) or []:
        claim = claim_by_id.get(claim_id, {})
        add("must_not_answer_from", claim.get("status") == "superseded" or bool(claim.get("superseded_by")), claim_id)

    if expected.get("must_flag_conflict"):
        add("must_flag_conflict", any(rel.get("relation") == "contradicts" for rel in relations), "contradicts relation")
    if expected.get("must_ask_for_resolution_without_overwrite"):
        add("must_ask_for_resolution_without_overwrite", any(rel.get("relation") == "contradicts" for rel in relations) and len(claims) >= 2)
    if expected.get("must_not_store_raw_secret"):
        proposed = json.dumps(setup.get("proposed_claims", []))
        safe = expected.get("safe_claim_text", "")
        redacted = all(pattern not in safe for pattern in expected.get("must_redact_patterns", []) or [])
        add("must_not_store_raw_secret", "sk-example" not in safe and redacted, {"proposed_contains_fake_secret": "sk-example" in proposed})
    if expected.get("answer_should_include"):
        combined = " ".join(claim.get("text", "") for claim in claims).lower()
        for phrase in expected["answer_should_include"]:
            add("answer_should_include", phrase.lower() in combined, phrase)

    report = {
        "ok": all(check["ok"] for check in checks),
        "retrieved": retrieved,
        "checks": checks,
    }
    if real_akbp:
        report["akbp"] = score_real_akbp(data)
        report["ok"] = report["ok"] and report["akbp"]["ok"]
    return report


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

    if not source_ids and not setup.get("proposed_claims"):
        issues.append("setup must include sources or proposed_claims")
    if len(relation_ids) != len(setup.get("relations", []) or []):
        issues.append("relations must have unique ids")
    return issues


def run(fixtures: Path, *, score: bool = False, real_akbp: bool = False) -> dict[str, Any]:
    scenarios = load_scenarios(fixtures)
    results = []
    for path, data in scenarios:
        issues = check_scenario(data)
        result = {
            "id": data.get("id", path.parent.name),
            "path": str(path.relative_to(ROOT)),
            "ok": not issues,
            "issues": issues,
        }
        if score and not issues:
            scoring = score_scenario(data, real_akbp=real_akbp)
            result["score"] = scoring
            result["ok"] = result["ok"] and scoring["ok"]
        results.append(result)
    return {
        "ok": all(item["ok"] for item in results) and bool(results),
        "mode": "akbp-score" if real_akbp else ("score" if score else "validate"),
        "count": len(results),
        "fixtures": str(fixtures.relative_to(ROOT) if fixtures.is_relative_to(ROOT) else fixtures),
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate AKBP benchmark fixtures.")
    parser.add_argument("--fixtures", default=str(DEFAULT_FIXTURES), help="Fixture directory containing */scenario.json files.")
    parser.add_argument("--score", action="store_true", help="Run deterministic fixture scoring checks.")
    parser.add_argument("--akbp", action="store_true", help="Populate a temporary AKBP knowledge base and check real query/context results.")
    args = parser.parse_args(argv)
    report = run(Path(args.fixtures).resolve(), score=args.score or args.akbp, real_akbp=args.akbp)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
