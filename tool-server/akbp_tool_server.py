#!/usr/bin/env python3
"""Minimal AKBP JSONL tool server.

This is intentionally dependency-free. It reads one JSON request per line from
stdin and writes one JSON response per line to stdout.
"""

from __future__ import annotations

import contextlib
import io
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "cli"))

import akbp  # noqa: E402

SCHEMA_BASE = "https://raw.githubusercontent.com/rohitg00/akbp/main/schemas"
REQUEST_SCHEMA = f"{SCHEMA_BASE}/tool-request.schema.json"
RESPONSE_SCHEMA = f"{SCHEMA_BASE}/tool-response.schema.json"
METHODS_SCHEMA = f"{SCHEMA_BASE}/tool-methods.schema.json"


def method_schema_ref(method: str) -> str | None:
    if method in METHODS:
        return f"{METHODS_SCHEMA}#/$defs/{method}.params"
    return None


WRITE_METHODS = {
    "akbp.remember",
    "akbp.source.add",
    "akbp.ingest",
    "akbp.import_apply",
    "akbp.index",
    "akbp.supersede",
    "akbp.contradict",
    "akbp.crystallize_session",
}

METHODS: dict[str, dict[str, Any]] = {
    "akbp.capabilities": {"write": False, "params": []},
    "akbp.status": {"write": False, "params": []},
    "akbp.query": {"write": False, "params": ["query", "limit"]},
    "akbp.context": {"write": False, "params": ["task", "limit"]},
    "akbp.index": {"write": True, "params": ["incremental", "dry_run"]},
    "akbp.search": {"write": False, "params": ["query", "limit"]},
    "akbp.remember": {"write": True, "params": ["text", "type", "evidence", "entity", "dry_run"]},
    "akbp.conformance": {"write": False, "params": ["level"]},
    "akbp.export": {"write": False, "params": []},
    "akbp.export_check": {"write": False, "params": ["file", "fail_on_issues"]},
    "akbp.audit": {"write": False, "params": ["limit"]},
    "akbp.cite": {"write": False, "params": ["claim_id"]},
    "akbp.source.add": {"write": True, "params": ["locator", "type", "title", "evidence", "dry_run"]},
    "akbp.source.verify": {"write": False, "params": ["source_id", "fail_on_issue"]},
    "akbp.ingest": {"write": True, "params": ["file", "type", "title", "claim", "claim_type", "confidence", "entity", "dry_run"]},
    "akbp.import_check": {"write": False, "params": ["file", "fail_on_rejected"]},
    "akbp.import_apply": {"write": True, "params": ["file", "dry_run"]},
    "akbp.supersede": {"write": True, "params": ["old_claim_id", "text", "type", "evidence", "entity", "dry_run"]},
    "akbp.contradict": {"write": True, "params": ["source_claim_id", "target_claim_id", "evidence", "dry_run"]},
    "akbp.crystallize_session": {"write": True, "params": ["transcript", "apply", "dry_run"]},
}

REQUIRED_PARAMS: dict[str, tuple[str, ...]] = {
    "akbp.query": ("query",),
    "akbp.context": ("task",),
    "akbp.search": ("query",),
    "akbp.remember": ("text",),
    "akbp.cite": ("claim_id",),
    "akbp.source.add": ("locator",),
    "akbp.ingest": ("file",),
    "akbp.export_check": ("file",),
    "akbp.import_check": ("file",),
    "akbp.import_apply": ("file",),
    "akbp.supersede": ("old_claim_id", "text"),
    "akbp.contradict": ("source_claim_id", "target_claim_id"),
    "akbp.crystallize_session": ("transcript",),
}


def run_cli(path: str, argv: list[str]) -> tuple[int, str, str]:
    out = io.StringIO()
    err = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = akbp.main(["--path", path, *argv])
    return int(code or 0), out.getvalue(), err.getvalue()


def error_response(request_id: Any, code: str, message: str, *, details: Any = None) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return {"id": request_id, "ok": False, "result": None, "error": error}


def capabilities() -> dict[str, Any]:
    return {
        "protocol": "akbp-jsonl-tool-server",
        "version": "0.1-draft",
        "features": {
            "structured_errors": True,
            "capability_discovery": True,
            "dry_run": True,
            "write_review_required": True,
            "write_apply_requires_approval": True,
            "jsonl_transport": True,
            "method_param_schemas": True,
            "unknown_param_rejection": True,
            "required_param_validation": True,
            "approval_required_errors": True,
        },
        "schemas": {
            "request": REQUEST_SCHEMA,
            "response": RESPONSE_SCHEMA,
            "methods": METHODS_SCHEMA,
        },
        "methods": {
            name: {
                **meta,
                "review_required": bool(meta.get("write")),
                **({"params_schema": ref} if (ref := method_schema_ref(name)) else {}),
            }
            for name, meta in METHODS.items()
        },
        "examples": [
            {"id": "status-1", "method": "akbp.status", "path": "."},
            {"id": "query-1", "method": "akbp.query", "path": ".", "params": {"query": "deployment", "limit": 5}},
            {"id": "search-1", "method": "akbp.search", "path": ".", "params": {"query": "deployment", "limit": 5}},
            {"id": "safe-write-1", "method": "akbp.remember", "path": ".", "dry_run": True, "params": {"text": "Agents need rollback paths"}},
            {"id": "safe-write-apply-1", "method": "akbp.remember", "path": ".", "approved": True, "params": {"text": "Agents need rollback paths"}},
            {"id": "ingest-1", "method": "akbp.ingest", "path": ".", "dry_run": True, "params": {"file": "notes.md", "claim": "The project ships small verified batches"}},
            {"id": "source-verify-1", "method": "akbp.source.verify", "path": ".", "params": {"source_id": "source_example", "fail_on_issue": True}},
            {"id": "export-check-1", "method": "akbp.export_check", "path": ".", "params": {"file": "bundle.json", "fail_on_issues": True}},
            {"id": "import-check-1", "method": "akbp.import_check", "path": ".", "params": {"file": "export.jsonl", "fail_on_rejected": True}},
            {"id": "import-apply-1", "method": "akbp.import_apply", "path": ".", "dry_run": True, "params": {"file": "export.jsonl"}},
            {"id": "crystallize-1", "method": "akbp.crystallize_session", "path": ".", "dry_run": True, "params": {"transcript": "session-summary.md", "apply": True}},
        ],
    }


def build_argv(method: str, params: dict[str, Any]) -> list[str]:
    mapping = {
        "akbp.status": ["status"],
        "akbp.query": ["query", params.get("query", ""), "--limit", str(params.get("limit", 10))],
        "akbp.context": ["context", params.get("task", ""), "--limit", str(params.get("limit", 10))],
        "akbp.index": ["index"],
        "akbp.search": ["search", params.get("query", ""), "--limit", str(params.get("limit", 10))],
        "akbp.remember": ["remember", params.get("text", ""), "--type", params.get("type", "observation")],
        "akbp.conformance": ["conformance", "--level", str(params.get("level", "0"))],
        "akbp.export": ["export"],
        "akbp.export_check": ["export-check", params.get("file", "")],
        "akbp.audit": ["audit", "--limit", str(params.get("limit", 20))],
        "akbp.cite": ["cite", params.get("claim_id", "")],
        "akbp.source.add": ["source", "add", params.get("locator", ""), "--type", params.get("type", "file")],
        "akbp.source.verify": ["source", "verify"],
        "akbp.ingest": ["ingest", params.get("file", ""), "--type", params.get("type", "file")],
        "akbp.import_check": ["import-check", params.get("file", "")],
        "akbp.import_apply": ["import-apply", params.get("file", "")],
        "akbp.supersede": ["supersede", params.get("old_claim_id", ""), params.get("text", ""), "--type", params.get("type", "observation")],
        "akbp.contradict": ["contradict", params.get("source_claim_id", ""), params.get("target_claim_id", "")],
        "akbp.crystallize_session": ["crystallize", params.get("transcript", "")],
    }
    argv = [str(a) for a in mapping[method] if a != ""]
    if method == "akbp.index" and params.get("incremental"):
        argv.append("--incremental")
    for evidence in params.get("evidence", []) or []:
        if method in WRITE_METHODS:
            argv.extend(["--evidence", str(evidence)])
    for entity in params.get("entity", []) or []:
        if method in {"akbp.remember", "akbp.supersede", "akbp.ingest"}:
            argv.extend(["--entity", str(entity)])
    if method == "akbp.source.verify" and params.get("source_id"):
        argv.append(str(params["source_id"]))
    if method == "akbp.source.verify" and params.get("fail_on_issue"):
        argv.append("--fail-on-issue")
    if method in {"akbp.source.add", "akbp.ingest"} and params.get("title"):
        argv.extend(["--title", str(params["title"])])
    if method == "akbp.crystallize_session" and params.get("apply"):
        argv.append("--apply")
    if method == "akbp.export_check" and params.get("fail_on_issues"):
        argv.append("--fail-on-issues")
    if method == "akbp.import_check" and params.get("fail_on_rejected"):
        argv.append("--fail-on-rejected")
    if method == "akbp.ingest":
        if params.get("claim"):
            argv.extend(["--claim", str(params["claim"])])
        if params.get("claim_type"):
            argv.extend(["--claim-type", str(params["claim_type"])])
        if params.get("confidence") is not None:
            argv.extend(["--confidence", str(params["confidence"])])
    return argv


def parse_payload(stdout: str) -> Any:
    if not stdout.strip():
        return None
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return stdout


def request_shape_errors(req: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if "id" not in req:
        errors.append("missing required field: id")
    elif not isinstance(req.get("id"), (str, int, float)) or isinstance(req.get("id"), bool):
        errors.append("id must be a string or number")
    if "method" not in req:
        errors.append("missing required field: method")
    elif not isinstance(req.get("method"), str) or not req.get("method", "").startswith("akbp."):
        errors.append("method must be an akbp.* string")
    if "path" in req and not isinstance(req.get("path"), str):
        errors.append("path must be a string")
    if "dry_run" in req and not isinstance(req.get("dry_run"), bool):
        errors.append("dry_run must be a boolean")
    if "approved" in req and not isinstance(req.get("approved"), bool):
        errors.append("approved must be a boolean")
    return errors


def missing_required_params(method: str, params: dict[str, Any]) -> list[str]:
    missing = []
    for name in REQUIRED_PARAMS.get(method, ()):
        value = params.get(name)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.append(name)
    return missing


def unknown_params(method: str, params: dict[str, Any]) -> list[str]:
    allowed = set(METHODS.get(method, {}).get("params", []))
    return sorted(name for name in params if name not in allowed)


def schema_enum(schema_name: str, property_name: str) -> set[str]:
    schema_path = ROOT / "schemas" / schema_name
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    return set(schema["properties"][property_name]["enum"])


CLAIM_TYPES = schema_enum("claim.schema.json", "type")
SOURCE_TYPES = schema_enum("source.schema.json", "type")

STRING_PARAMS = {
    "query",
    "task",
    "text",
    "type",
    "locator",
    "title",
    "file",
    "claim",
    "claim_type",
    "old_claim_id",
    "source_id",
    "source_claim_id",
    "target_claim_id",
    "transcript",
    "level",
    "claim_id",
}


def param_type_errors(method: str, params: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for name in sorted(STRING_PARAMS.intersection(params)):
        if not isinstance(params.get(name), str):
            errors.append(f"{name} must be a string")
    if "type" in params and method in {"akbp.remember", "akbp.supersede"} and params.get("type") not in CLAIM_TYPES:
        errors.append("type must be one of: " + ", ".join(sorted(CLAIM_TYPES)))
    if "type" in params and method in {"akbp.source.add", "akbp.ingest"} and params.get("type") not in SOURCE_TYPES:
        errors.append("type must be one of: " + ", ".join(sorted(SOURCE_TYPES)))
    if "claim_type" in params and method == "akbp.ingest" and params.get("claim_type") not in CLAIM_TYPES:
        errors.append("claim_type must be one of: " + ", ".join(sorted(CLAIM_TYPES)))
    if "dry_run" in params and not isinstance(params.get("dry_run"), bool):
        errors.append("dry_run must be a boolean")
    if "limit" in params:
        limit = params.get("limit")
        if not isinstance(limit, int) or isinstance(limit, bool):
            errors.append("limit must be an integer")
        elif limit < 1 or limit > 100:
            errors.append("limit must be between 1 and 100")
    if "confidence" in params:
        confidence = params.get("confidence")
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
            errors.append("confidence must be a number")
        elif confidence < 0 or confidence > 1:
            errors.append("confidence must be between 0 and 1")
    if "incremental" in params and not isinstance(params.get("incremental"), bool):
        errors.append("incremental must be a boolean")
    if "fail_on_rejected" in params and not isinstance(params.get("fail_on_rejected"), bool):
        errors.append("fail_on_rejected must be a boolean")
    if "fail_on_issue" in params and not isinstance(params.get("fail_on_issue"), bool):
        errors.append("fail_on_issue must be a boolean")
    if "fail_on_issues" in params and not isinstance(params.get("fail_on_issues"), bool):
        errors.append("fail_on_issues must be a boolean")
    if "evidence" in params:
        evidence = params.get("evidence")
        if not isinstance(evidence, list):
            errors.append("evidence must be an array")
        elif any(not isinstance(item, str) for item in evidence):
            errors.append("evidence items must be strings")
    if "entity" in params:
        entity = params.get("entity")
        if not isinstance(entity, list):
            errors.append("entity must be an array")
        elif any(not isinstance(item, str) for item in entity):
            errors.append("entity items must be strings")
    if method == "akbp.crystallize_session" and "apply" in params and not isinstance(params.get("apply"), bool):
        errors.append("apply must be a boolean")
    return errors


def handle(req: dict[str, Any]) -> dict[str, Any]:
    request_id = req.get("id")
    shape_errors = request_shape_errors(req)
    if shape_errors:
        return error_response(request_id, "invalid_request", "request does not match AKBP tool request envelope", details={"errors": shape_errors, "schema": REQUEST_SCHEMA})

    method = req.get("method")
    path = str(req.get("path", "."))
    params = req.get("params", {}) or {}

    if method == "akbp.capabilities":
        return {"id": request_id, "ok": True, "result": capabilities(), "error": None}
    if method not in METHODS:
        return error_response(request_id, "unknown_method", f"unknown method: {method}", details={"available_methods": sorted(METHODS)})
    if not isinstance(params, dict):
        return error_response(request_id, "invalid_params", "params must be an object", details={"params_schema": method_schema_ref(method), "type_errors": ["params must be an object"]})
    dry_run = bool(req.get("dry_run") or params.get("dry_run"))

    unknown = unknown_params(method, params)
    if unknown:
        return error_response(
            request_id,
            "invalid_params",
            f"unknown params for {method}: {', '.join(unknown)}",
            details={"unknown": unknown, "allowed": METHODS[method]["params"], "params_schema": method_schema_ref(method)},
        )

    type_errors = param_type_errors(method, params)
    if type_errors:
        return error_response(
            request_id,
            "invalid_params",
            f"invalid parameter types for {method}",
            details={"type_errors": type_errors, "params_schema": method_schema_ref(method)},
        )

    missing = missing_required_params(method, params)
    if missing:
        return error_response(
            request_id,
            "invalid_params",
            f"missing required params for {method}: {', '.join(missing)}",
            details={"missing": missing, "params_schema": method_schema_ref(method)},
        )

    argv = build_argv(method, params)
    if dry_run and method == "akbp.ingest":
        code, stdout, stderr = run_cli(path, [*argv, "--dry-run"])
        if code != 0:
            return error_response(request_id, "cli_error", stderr.strip() or "AKBP command failed", details={"method": method, "exit_code": code, "stdout": stdout})
        result = parse_payload(stdout)
        if isinstance(result, dict):
            result.setdefault("review_required", True)
            result.setdefault("apply_instruction", "Repeat the same request without dry_run only after reviewing redaction status, extracted signals, claim ids, would_write paths, and approval or trusted local policy.")
        return {"id": request_id, "ok": True, "result": result, "error": None}

    if dry_run and method == "akbp.import_apply":
        code, stdout, stderr = run_cli(path, [*argv, "--dry-run"])
        if code != 0 and not stdout.strip():
            return error_response(request_id, "cli_error", stderr.strip() or "AKBP command failed", details={"method": method, "exit_code": code, "stdout": stdout})
        result = parse_payload(stdout)
        if isinstance(result, dict):
            result.setdefault("review_required", True)
            result.setdefault("apply_instruction", "Repeat the same request with approved:true only after reviewing import-check output and dry-run would_write ids.")
        return {"id": request_id, "ok": True, "result": result, "error": None}

    if dry_run and method in WRITE_METHODS:
        return {
            "id": request_id,
            "ok": True,
            "result": {
                "dry_run": True,
                "method": method,
                "path": path,
                "argv": argv,
                "would_write": True,
                "review_required": True,
                "apply_instruction": "Repeat the same request without dry_run only after user approval or trusted local policy.",
            },
            "error": None,
        }

    if method in WRITE_METHODS and not bool(req.get("approved")):
        return error_response(
            request_id,
            "approval_required",
            f"{method} requires approved:true for non-dry-run writes",
            details={
                "method": method,
                "dry_run": False,
                "review_required": True,
                "apply_instruction": "Repeat the same request with approved:true only after user approval or trusted local policy.",
            },
        )

    if method == "akbp.import_apply":
        argv = [*argv, "--approved"]
    code, stdout, stderr = run_cli(path, argv)
    if method in {"akbp.import_check", "akbp.import_apply", "akbp.source.verify"} and stdout.strip():
        return {"id": request_id, "ok": True, "result": parse_payload(stdout), "error": None}
    if code != 0:
        return error_response(request_id, "cli_error", stderr.strip() or "AKBP command failed", details={"method": method, "exit_code": code, "stdout": stdout})
    return {"id": request_id, "ok": True, "result": parse_payload(stdout), "error": None}


def main() -> int:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        request_id = None
        try:
            req = json.loads(line)
            if not isinstance(req, dict):
                print(json.dumps(error_response(None, "invalid_request", "request must be a JSON object"), ensure_ascii=False), flush=True)
                continue
            request_id = req.get("id")
            res = handle(req)
        except json.JSONDecodeError as exc:
            res = error_response(
                None,
                "invalid_json",
                "line is not valid JSON",
                details={"errors": [str(exc)], "schema": REQUEST_SCHEMA},
            )
        except Exception as exc:  # pragma: no cover - defensive server boundary
            res = error_response(request_id, "internal_error", "internal server error", details={"errors": [str(exc)]})
        print(json.dumps(res, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
