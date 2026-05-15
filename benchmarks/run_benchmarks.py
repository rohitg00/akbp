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
    if fixtures.is_file():
        paths = [fixtures]
    elif (fixtures / "scenario.json").exists():
        paths = [fixtures / "scenario.json"]
    else:
        paths = sorted(fixtures.glob("*/scenario.json"))
    for path in paths:
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


def response_schema() -> dict[str, Any]:
    return json.loads((ROOT / "schemas" / "tool-response.schema.json").read_text(encoding="utf-8"))


def schema_def(schema_ref: str) -> dict[str, Any]:
    schema = response_schema()
    prefix = "#/$defs/"
    if not schema_ref.startswith(prefix):
        raise ValueError(f"unsupported schema ref: {schema_ref}")
    return schema["$defs"][schema_ref[len(prefix):]]


def resolve_schema_ref(schema: dict[str, Any], schema_ref: str) -> dict[str, Any]:
    prefix = "#/$defs/"
    if not schema_ref.startswith(prefix):
        raise ValueError(f"unsupported schema ref: {schema_ref}")
    return schema["$defs"][schema_ref[len(prefix):]]


def schema_shape_issues(payload: Any, definition: dict[str, Any], *, path: str = "$", root_schema: dict[str, Any] | None = None) -> list[str]:
    root = root_schema or response_schema()
    if "$ref" in definition:
        definition = resolve_schema_ref(root, definition["$ref"])
    issues: list[str] = []
    expected_type = definition.get("type")
    if expected_type == "object":
        if not isinstance(payload, dict):
            return [f"{path} expected object"]
        required = definition.get("required", []) or []
        for field in required:
            if field not in payload:
                issues.append(f"{path} missing required field {field}")
        properties = definition.get("properties", {}) or {}
        if definition.get("additionalProperties") is False:
            for field in payload:
                if field not in properties:
                    issues.append(f"{path} unexpected field {field}")
        for field, child_schema in properties.items():
            if field in payload:
                issues.extend(schema_shape_issues(payload[field], child_schema, path=f"{path}.{field}", root_schema=root))
    elif expected_type == "array":
        if not isinstance(payload, list):
            return [f"{path} expected array"]
        item_schema = definition.get("items")
        if item_schema:
            for index, item in enumerate(payload):
                issues.extend(schema_shape_issues(item, item_schema, path=f"{path}[{index}]", root_schema=root))
    elif expected_type == "string" and not isinstance(payload, str):
        issues.append(f"{path} expected string")
    elif expected_type == "boolean" and not isinstance(payload, bool):
        issues.append(f"{path} expected boolean")
    elif expected_type == "number" and not isinstance(payload, (int, float)):
        issues.append(f"{path} expected number")
    elif expected_type == "integer" and not isinstance(payload, int):
        issues.append(f"{path} expected integer")
    if "const" in definition and payload != definition["const"]:
        issues.append(f"{path} expected const {definition['const']!r}")
    if "enum" in definition and payload not in definition["enum"]:
        issues.append(f"{path} expected one of {definition['enum']!r}")
    return issues


def split_nested_path(path: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    escaped = False
    for char in path:
        if escaped:
            current.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == ".":
            parts.append("".join(current))
            current = []
        else:
            current.append(char)
    if escaped:
        current.append("\\")
    parts.append("".join(current))
    return parts


def nested_values(payload: Any, path: str) -> list[Any]:
    values = [payload]
    for part in split_nested_path(path):
        next_values: list[Any] = []
        collect_list = part.endswith("[]")
        key = part[:-2] if collect_list else part
        for value in values:
            if isinstance(value, dict) and key in value:
                child = value[key]
                if collect_list and isinstance(child, list):
                    next_values.extend(child)
                else:
                    next_values.append(child)
        values = next_values
    return values


def missing_nested_contains(payload: Any, expected: dict[str, list[Any]]) -> dict[str, list[Any]]:
    missing: dict[str, list[Any]] = {}
    for path, required_values in expected.items():
        found = nested_values(payload, path)
        absent = [value for value in required_values if value not in found]
        if absent:
            missing[path] = absent
    return missing


def run_tool_server(requests: list[dict[str, Any]], kb: Path) -> list[dict[str, Any]]:
    envelopes = []
    for request in requests:
        envelope = {
            "id": request["id"],
            "path": str(kb),
            "method": request["method"],
            "approved": bool(request.get("approved")),
            "params": request.get("params", {}),
        }
        envelopes.append(json.dumps(envelope, sort_keys=True))
    proc = subprocess.run(
        [sys.executable, str(ROOT / "tool-server" / "akbp_tool_server.py")],
        input="\n".join(envelopes) + "\n",
        text=True,
        capture_output=True,
        check=True,
    )
    return [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]


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
    entities = []
    for entity in setup.get("entities", []) or []:
        entities.append({
            "id": entity["id"],
            "name": entity["name"],
            "type": entity.get("type", "concept"),
            "aliases": entity.get("aliases", []),
            "description": entity.get("description"),
            "page": entity.get("page"),
            "created_at": entity.get("created_at", "2026-01-01T00:00:00Z"),
            "updated_at": entity.get("updated_at", "2026-01-01T00:00:00Z"),
        })
    relations = []
    for relation in setup.get("relations", []) or []:
        relations.append({
            "id": relation["id"],
            "source": relation["source"],
            "target": relation["target"],
            "relation": relation.get("relation", "related_to"),
            "confidence": relation.get("confidence", 0.5),
            "evidence": relation.get("evidence", []),
            "created_at": relation.get("created_at", "2026-01-01T00:00:00Z"),
            "updated_at": relation.get("updated_at", "2026-01-01T00:00:00Z"),
        })
    write_jsonl(kb / "raw" / "sources" / "sources.jsonl", sources)
    write_jsonl(kb / "claims" / "claims.jsonl", claims)
    write_jsonl(kb / "graph" / "entities.jsonl", entities)
    write_jsonl(kb / "graph" / "relations.jsonl", relations)
    if claims or sources or entities or relations:
        run_cli(kb, "index")


def score_real_akbp(data: dict[str, Any]) -> dict[str, Any]:
    setup = data.get("setup", {})
    if not setup.get("claims") and not setup.get("tool_server_requests"):
        return {"ok": True, "skipped": "scenario has no stored claims"}
    with tempfile.TemporaryDirectory() as d:
        kb = Path(d) / "kb"
        scenario_to_kb(data, kb)
        query = run_cli(kb, "query", data.get("query", ""), "--limit", "20")
        context = run_cli(kb, "context", data.get("query", ""), "--limit", "20")
        tool_outputs = run_tool_server(setup.get("tool_server_requests", []) or [], kb) if setup.get("tool_server_requests") else []
    expected = data.get("expected", {})
    query_ids = {item.get("id") for item in query.get("results", [])}
    context_items = context.get("items", []) if isinstance(context.get("items"), list) else []
    context_ids = {item.get("id") for item in context_items if isinstance(item, dict)}
    context_citation_ids = {citation for item in context_items if isinstance(item, dict) for citation in (item.get("citations", []) or [])}
    checks = []
    for claim_id in expected.get("must_retrieve", []) or []:
        checks.append({
            "name": "akbp_query_or_context_must_retrieve",
            "ok": claim_id in query_ids or claim_id in context_ids,
            "details": claim_id,
        })
    for source_id in expected.get("must_cite_in_context", []) or []:
        checks.append({
            "name": "akbp_context_must_cite",
            "ok": source_id in context_citation_ids,
            "details": source_id,
        })
    requests = setup.get("tool_server_requests", []) or []
    output_by_id = {output.get("id"): output for output in tool_outputs}
    for request in requests:
        output = output_by_id.get(request.get("id"), {})
        if request.get("expected_error_code"):
            error = output.get("error") if isinstance(output.get("error"), dict) else {}
            details = error.get("details") if isinstance(error.get("details"), dict) else {}
            missing = [field for field in request.get("expected_error_fields", []) or [] if field not in details]
            mismatched = {key: {"expected": value, "actual": details.get(key)} for key, value in (request.get("expected_error_values", {}) or {}).items() if details.get(key) != value}
            schema_issues = schema_shape_issues(details, schema_def(request["expected_error_schema"])) if request.get("expected_error_schema") else []
            missing_contains = missing_nested_contains(details, request.get("expected_error_contains", {}) or {})
            checks.append({
                "name": "akbp_tool_rejection_shape",
                "ok": output.get("ok") is False and error.get("code") == request.get("expected_error_code") and not missing and not mismatched and not schema_issues and not missing_contains,
                "details": {"id": request.get("id"), "method": request.get("method"), "missing": missing, "mismatched": mismatched, "missing_contains": missing_contains, "schema_issues": schema_issues, "schema": request.get("expected_error_schema"), "code": error.get("code")},
            })
            continue
        result = output.get("result") if isinstance(output.get("result"), dict) else {}
        missing = [field for field in request.get("expected_result_fields", []) or [] if field not in result]
        mismatched = {key: {"expected": value, "actual": result.get(key)} for key, value in (request.get("expected_result_values", {}) or {}).items() if result.get(key) != value}
        schema_issues = schema_shape_issues(result, schema_def(request["expected_result_schema"])) if request.get("expected_result_schema") else []
        missing_contains = missing_nested_contains(result, request.get("expected_result_contains", {}) or {})
        checks.append({
            "name": "akbp_tool_apply_response_shape",
            "ok": bool(output.get("ok")) and not missing and not mismatched and not schema_issues and not missing_contains,
            "details": {"id": request.get("id"), "method": request.get("method"), "missing": missing, "mismatched": mismatched, "missing_contains": missing_contains, "schema_issues": schema_issues, "schema": request.get("expected_result_schema")},
        })
    return {
        "ok": all(check["ok"] for check in checks),
        "query_result_ids": sorted(x for x in query_ids if x),
        "context_item_ids": sorted(x for x in context_ids if x),
        "context_citation_ids": sorted(x for x in context_citation_ids if x),
        "tool_output_ids": sorted(x for x in output_by_id if x),
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

    import_objects = setup.get("import_objects", []) or []
    import_by_id = {item.get("id"): item for item in import_objects}
    redaction_patterns = expected.get("must_redact_patterns", []) or []
    safe_claim_text = expected.get("safe_claim_text", "")
    if expected.get("must_reject_import_ids"):
        for import_id in expected["must_reject_import_ids"]:
            raw = json.dumps(import_by_id.get(import_id, {}))
            add("must_reject_import_id", any(pattern in raw for pattern in redaction_patterns), import_id)
    if expected.get("must_allow_import_ids"):
        for import_id in expected["must_allow_import_ids"]:
            raw = json.dumps(import_by_id.get(import_id, {}))
            add("must_allow_import_id", import_id in import_by_id and not any(pattern in raw for pattern in redaction_patterns), import_id)
    if redaction_patterns and safe_claim_text:
        add("safe_claim_text_redacts_patterns", not any(pattern in safe_claim_text for pattern in redaction_patterns), redaction_patterns)
    if expected.get("answer_should_include"):
        import_objects = setup.get("import_objects", []) or []
        tool_requests = setup.get("tool_server_requests", []) or []
        combined = " ".join(
            [claim.get("text", "") for claim in claims]
            + [str(item.get("text", "")) for item in import_objects]
            + [json.dumps(request, sort_keys=True) for request in tool_requests]
            + [str(expected.get("safe_claim_text", ""))]
            + [str(data.get("task", "")), str(data.get("query", ""))]
        ).lower()
        for phrase in expected["answer_should_include"]:
            add("answer_should_include", phrase.lower() in combined, phrase)
    if expected.get("must_apply_tool_methods"):
        requested_methods = {request.get("method") for request in setup.get("tool_server_requests", []) or [] if request.get("approved") is True}
        for method in expected["must_apply_tool_methods"]:
            add("must_apply_tool_method", method in requested_methods, method)
    if expected.get("must_reject_tool_methods"):
        rejected_methods = {request.get("method") for request in setup.get("tool_server_requests", []) or [] if request.get("expected_error_code")}
        for method in expected["must_reject_tool_methods"]:
            add("must_reject_tool_method", method in rejected_methods, method)
    if expected.get("must_dry_run_tool_methods"):
        dry_run_methods = {request.get("method") for request in setup.get("tool_server_requests", []) or [] if request.get("params", {}).get("dry_run") is True}
        for method in expected["must_dry_run_tool_methods"]:
            add("must_dry_run_tool_method", method in dry_run_methods, method)

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
    entity_ids = ids(setup.get("entities", []) or [])
    graph_node_ids = claim_ids | entity_ids
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
        if relation.get("source") not in graph_node_ids:
            issues.append(f"relation {relation.get('id')} has missing source graph node")
        if relation.get("target") not in graph_node_ids:
            issues.append(f"relation {relation.get('id')} has missing target graph node")
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

    if not source_ids and not entity_ids and not setup.get("proposed_claims") and not setup.get("import_objects") and not setup.get("tool_server_requests"):
        issues.append("setup must include sources, entities, proposed_claims, import_objects, or tool_server_requests")

    import_ids = ids(setup.get("import_objects", []) or [])
    if len(import_ids) != len(setup.get("import_objects", []) or []):
        issues.append("import_objects must have unique ids")
    for import_id in expected.get("must_reject_import_ids", []) or []:
        if import_id not in import_ids:
            issues.append(f"expected must_reject_import_ids missing import object {import_id}")
    for import_id in expected.get("must_allow_import_ids", []) or []:
        if import_id not in import_ids:
            issues.append(f"expected must_allow_import_ids missing import object {import_id}")
    tool_requests = setup.get("tool_server_requests", []) or []
    request_ids = ids(tool_requests)
    if len(request_ids) != len(tool_requests):
        issues.append("tool_server_requests must have unique ids")
    requested_methods = {request.get("method") for request in tool_requests if request.get("approved") is True}
    for method in expected.get("must_apply_tool_methods", []) or []:
        if method not in requested_methods:
            issues.append(f"expected must_apply_tool_methods missing approved request for {method}")
    rejected_methods = {request.get("method") for request in tool_requests if request.get("expected_error_code")}
    for method in expected.get("must_reject_tool_methods", []) or []:
        if method not in rejected_methods:
            issues.append(f"expected must_reject_tool_methods missing rejection request for {method}")
    dry_run_methods = {request.get("method") for request in tool_requests if isinstance(request.get("params"), dict) and request.get("params", {}).get("dry_run") is True}
    for method in expected.get("must_dry_run_tool_methods", []) or []:
        if method not in dry_run_methods:
            issues.append(f"expected must_dry_run_tool_methods missing dry-run request for {method}")
    for request in tool_requests:
        if not request.get("expected_result_fields") and not request.get("expected_error_code"):
            issues.append(f"tool request {request.get('id')} must declare expected_result_fields or expected_error_code")
        if request.get("expected_result_schema"):
            try:
                schema_def(request["expected_result_schema"])
            except (KeyError, ValueError) as exc:
                issues.append(f"tool request {request.get('id')} has invalid expected_result_schema: {exc}")
        if request.get("expected_error_schema"):
            try:
                schema_def(request["expected_error_schema"])
            except (KeyError, ValueError) as exc:
                issues.append(f"tool request {request.get('id')} has invalid expected_error_schema: {exc}")
        for field in (request.get("expected_result_values", {}) or {}):
            if field not in (request.get("expected_result_fields", []) or []):
                issues.append(f"tool request {request.get('id')} expected_result_values field {field} must also be listed in expected_result_fields")
        for field in (request.get("expected_error_values", {}) or {}):
            if field not in (request.get("expected_error_fields", []) or []):
                issues.append(f"tool request {request.get('id')} expected_error_values field {field} must also be listed in expected_error_fields")
    if len(entity_ids) != len(setup.get("entities", []) or []):
        issues.append("entities must have unique ids")
    if len(relation_ids) != len(setup.get("relations", []) or []):
        issues.append("relations must have unique ids")
    return issues


def scenario_profiles(data: dict[str, Any]) -> set[str]:
    profiles = data.get("profiles", []) or []
    if not isinstance(profiles, list):
        return set()
    return {str(profile) for profile in profiles}


def run(fixtures: Path, *, score: bool = False, real_akbp: bool = False, profile: str | None = None) -> dict[str, Any]:
    scenarios = load_scenarios(fixtures)
    if profile:
        scenarios = [(path, data) for path, data in scenarios if profile in scenario_profiles(data)]
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
        "profile": profile,
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate AKBP benchmark fixtures.")
    parser.add_argument("--fixtures", default=str(DEFAULT_FIXTURES), help="Fixture directory containing */scenario.json files.")
    parser.add_argument("--score", action="store_true", help="Run deterministic fixture scoring checks.")
    parser.add_argument("--akbp", action="store_true", help="Populate a temporary AKBP knowledge base and check real query/context results.")
    parser.add_argument("--profile", help="Run only fixtures tagged with this profile, for example adapter-quality.")
    args = parser.parse_args(argv)
    report = run(Path(args.fixtures).resolve(), score=args.score or args.akbp, real_akbp=args.akbp, profile=args.profile)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
