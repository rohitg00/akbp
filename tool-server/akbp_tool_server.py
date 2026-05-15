#!/usr/bin/env python3
"""Minimal AKBP JSONL tool server.

This is intentionally dependency-free. It reads one JSON request per line from
stdin and writes one JSON response per line to stdout.
"""

from __future__ import annotations

import contextlib
import io
import json
import math
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
MAX_REQUEST_BYTES = 1048576
MAX_REQUEST_ID_LENGTH = 512
MAX_REQUEST_ID_ABS_VALUE = 9007199254740991
MAX_ERROR_OUTPUT_BYTES = 8192
ALLOWED_REQUEST_FIELDS = {"id", "method", "path", "dry_run", "approved", "params"}
PARAM_LIST_LIMITS = {
    "evidence": {"max_items": 64, "max_item_length": 512},
    "entity": {"max_items": 128, "max_item_length": 256},
}

PARAM_MAX_LENGTHS = {
    "query": 4096,
    "task": 8192,
    "text": 65536,
    "transcript": 65536,
    "claim": 65536,
    "title": 512,
    "file": 4096,
    "locator": 4096,
    "source_id": 512,
    "claim_id": 512,
    "old_claim_id": 512,
    "source_claim_id": 512,
    "target_claim_id": 512,
    "type": 64,
    "claim_type": 64,
    "level": 16,
    "profile": 64,
}


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
    "akbp.session.end",
}

METHODS: dict[str, dict[str, Any]] = {
    "akbp.capabilities": {"write": False, "params": ["client", "requires", "requires_profiles", "requires_methods"]},
    "akbp.status": {"write": False, "params": ["limit"]},
    "akbp.doctor": {"write": False, "params": ["profile"]},
    "akbp.query": {"write": False, "params": ["query", "limit"]},
    "akbp.context": {"write": False, "params": ["task", "limit", "max_chars", "min_items", "require_citations"]},
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
    "akbp.session.start": {"write": False, "params": ["task", "query", "limit", "max_chars", "min_items", "require_citations"]},
    "akbp.session.end": {"write": True, "params": ["transcript", "apply", "dry_run"]},
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
    "akbp.source.verify": ("source_id",),
    "akbp.supersede": ("old_claim_id", "text"),
    "akbp.contradict": ("source_claim_id", "target_claim_id"),
    "akbp.crystallize_session": ("transcript",),
    "akbp.session.end": ("transcript",),
}

CAPABILITY_PROFILES: dict[str, list[str]] = {
    "read_only": [
        "akbp.capabilities",
        "akbp.status",
        "akbp.doctor",
        "akbp.query",
        "akbp.context",
        "akbp.search",
        "akbp.conformance",
        "akbp.export",
        "akbp.export_check",
        "akbp.audit",
        "akbp.cite",
        "akbp.source.verify",
        "akbp.import_check",
        "akbp.session.start",
    ],
    "startup_context": ["akbp.capabilities", "akbp.status", "akbp.session.start", "akbp.context", "akbp.search"],
    "reviewed_write": ["akbp.remember", "akbp.ingest", "akbp.source.add", "akbp.session.end"],
    "lifecycle": ["akbp.supersede", "akbp.contradict", "akbp.crystallize_session", "akbp.audit", "akbp.cite"],
    "portability": ["akbp.export", "akbp.export_check", "akbp.import_check", "akbp.import_apply"],
    "maintenance": ["akbp.doctor", "akbp.index", "akbp.source.verify", "akbp.conformance"],
}

PROFILE_CONTRACTS: dict[str, dict[str, Any]] = {
    "startup_context": {
        "purpose": "Fetch bounded cited context at session start without enabling durable writes.",
        "default_for": ["new adapters", "fresh sessions", "hosts without write review UI"],
        "risk": "low",
        "requires_review_surface": False,
        "write_policy": "no_writes",
        "ready_field": "adapter_readiness.startup_context_ready",
    },
    "read_only": {
        "purpose": "Expose retrieval, citation, source verification, and import/export checks while keeping writes disabled.",
        "default_for": ["hosted tools", "remote bridges", "first integration pass"],
        "risk": "low",
        "requires_review_surface": False,
        "write_policy": "no_writes",
        "ready_field": "adapter_readiness.read_only_ready",
    },
    "reviewed_write": {
        "purpose": "Allow durable memory proposals only through dry-run previews followed by exact approved apply calls.",
        "default_for": ["local interactive adapters with visible review", "trusted setup scripts with external approval"],
        "risk": "medium",
        "requires_review_surface": True,
        "write_policy": "dry_run_preview_then_approved_apply",
        "ready_field": "adapter_readiness.reviewed_write_ready",
    },
    "lifecycle": {
        "purpose": "Represent supersession, contradiction, crystallization, audit, and citation lifecycle operations.",
        "default_for": ["maintenance tools", "advanced adapters after reviewed-write readiness"],
        "risk": "medium",
        "requires_review_surface": True,
        "write_policy": "dry_run_preview_then_approved_apply_for_write_methods",
        "ready_field": "adapter_readiness.reviewed_write_ready",
    },
    "portability": {
        "purpose": "Check, export, import-check, and reviewed import-apply portable knowledge bundles.",
        "default_for": ["migration helpers", "bundle sharing", "adapter installers"],
        "risk": "medium",
        "requires_review_surface": True,
        "write_policy": "import_check_before_import_apply",
        "ready_field": "adapter_readiness.read_only_ready",
    },
    "maintenance": {
        "purpose": "Keep sources, indexes, conformance, and adapter readiness healthy before relying on recalled memory.",
        "default_for": ["release checks", "adapter setup checks", "scheduled local maintenance"],
        "risk": "low",
        "requires_review_surface": False,
        "write_policy": "index_requires_approved_apply_when_dispatched_through_tool_server",
        "ready_field": "adapter_readiness.recommended_profile",
    },
}

KNOWLEDGE_CAPABILITY: dict[str, Any] = {
    "kind": "agent_knowledge_base",
    "artifact_model": "file_backed_jsonl",
    "transport": "jsonl-stdio",
    "scope": "caller_supplied_local_path",
    "trust_model": "cited_review_gated_memory",
    "retrieval": {
        "bounded_context": True,
        "citations_required_for_trusted_context": True,
        "startup_method": "akbp.session.start",
        "search_methods": ["akbp.context", "akbp.search", "akbp.query"],
    },
    "writes": {
        "enabled": True,
        "policy": "dry_run_preview_then_approved_apply",
        "preview_flag": "dry_run",
        "approval_flag": "approved",
        "approval_required_error": "approval_required",
    },
    "session_boundary": {
        "transient_state_policy": "runtime_owned_until_reviewed_promotion",
        "promotion_method": "akbp.session.end",
        "promotion_preview_flag": "dry_run",
        "durable_apply_flag": "approved",
        "reject_uncited_transient_state": True,
        "promotion_contract": {
            "durable_candidate_types": ["decision", "workflow", "preference", "fact", "blocker"],
            "preview_must_surface": ["review_required", "apply_instruction", "warnings", "source_ids", "skipped_claims", "would_write"],
            "apply_requires_same_request": True,
            "apply_requires_reviewed_summary": True,
            "reject_inputs": ["raw_transcript", "scratch_reasoning", "secrets", "private_messages", "uncited_claims"],
        },
    },
    "portability": {
        "export_method": "akbp.export",
        "import_check_method": "akbp.import_check",
        "import_apply_method": "akbp.import_apply",
    },
}


def fallback_method_schema_defs() -> dict[str, Any]:
    return {
        f"{method}.params": {
            "properties": {name: {} for name in meta.get("params", [])},
            "required": list(REQUIRED_PARAMS.get(method, ())),
        }
        for method, meta in METHODS.items()
    }


def load_method_schema_defs() -> dict[str, Any]:
    schema_path = ROOT / "schemas" / "tool-methods.schema.json"
    if not schema_path.exists():
        return fallback_method_schema_defs()
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    return schema.get("$defs", {})


def method_schema_runtime_errors() -> list[str]:
    errors: list[str] = []
    defs = load_method_schema_defs()
    methods = set(METHODS)
    schema_methods = {name.removesuffix(".params") for name in defs if name.startswith("akbp.") and name.endswith(".params")}
    for method in sorted(methods - schema_methods):
        errors.append(f"{method} is missing from tool-methods.schema.json")
    for method in sorted(schema_methods - methods):
        errors.append(f"{method} is documented in tool-methods.schema.json but not implemented")
    for method in sorted(methods & schema_methods):
        definition = defs[f"{method}.params"]
        runtime_params = set(METHODS[method].get("params", []))
        schema_params = set(definition.get("properties", {}))
        if runtime_params != schema_params:
            errors.append(
                f"{method} params differ from schema: "
                f"runtime={sorted(runtime_params)} schema={sorted(schema_params)}"
            )
        runtime_required = tuple(REQUIRED_PARAMS.get(method, ()))
        schema_required = tuple(definition.get("required", []))
        if runtime_required != schema_required:
            errors.append(
                f"{method} required params differ from schema: "
                f"runtime={list(runtime_required)} schema={list(schema_required)}"
            )
    return errors


SCHEMA_RUNTIME_ERRORS = method_schema_runtime_errors()


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


def invalid_request_response(request_id: Any, errors: list[str], message: str = "request does not match AKBP tool request envelope") -> dict[str, Any]:
    return error_response(
        request_id,
        "invalid_request",
        message,
        details={"errors": errors, "schema": REQUEST_SCHEMA},
    )


def cli_error_response(request_id: Any, method: str, code: int, stdout: str, stderr: str) -> dict[str, Any]:
    redacted_stdout = akbp.redact_text(stdout)
    redacted_stderr = akbp.redact_text(stderr.strip())
    safe_stdout, stdout_truncated = truncate_text(redacted_stdout, MAX_ERROR_OUTPUT_BYTES)
    safe_stderr, stderr_truncated = truncate_text(redacted_stderr, MAX_ERROR_OUTPUT_BYTES)
    return error_response(
        request_id,
        "cli_error",
        safe_stderr or "AKBP command failed",
        details={
            "method": method,
            "exit_code": code,
            "stdout": safe_stdout,
            "redacted": redacted_stdout != stdout or redacted_stderr != stderr.strip(),
            "truncated": stdout_truncated or stderr_truncated,
        },
    )


def capability_features() -> dict[str, bool]:
    return {
            "structured_errors": True,
            "capability_discovery": True,
            "dry_run": True,
            "write_review_required": True,
            "write_apply_requires_approval": True,
            "jsonl_transport": True,
            "method_param_schemas": True,
            "bounded_context": True,
            "session_lifecycle_entrypoints": True,
            "session_boundary_contract": True,
            "method_schema_runtime_parity": not SCHEMA_RUNTIME_ERRORS,
            "unknown_request_field_rejection": True,
            "unknown_param_rejection": True,
            "required_param_validation": True,
            "approval_required_errors": True,
            "max_request_bytes_enforced": True,
            "path_validation": True,
            "param_length_validation": True,
            "param_min_length_validation": True,
            "param_control_char_validation": True,
            "param_array_validation": True,
            "param_enum_validation": True,
            "param_numeric_range_validation": True,
            "finite_numeric_param_validation": True,
            "dry_run_argv_redaction": True,
            "cli_error_redaction": True,
            "strict_json_parse": True,
            "strict_json_output": True,
            "finite_request_id_validation": True,
            "request_id_string_validation": True,
            "request_id_numeric_bounds": True,
            "cli_error_output_truncation": True,
            "capability_negotiation": True,
        }


def normalize_feature_name(name: str) -> str:
    return name.removeprefix("features.")


def negotiation_result(params: dict[str, Any], features: dict[str, bool]) -> dict[str, Any]:
    requested = list(params.get("requires", []) or [])
    supported = [name for name in requested if features.get(normalize_feature_name(name)) is True]
    unsupported = [name for name in requested if features.get(normalize_feature_name(name)) is not True]
    requested_profiles = list(params.get("requires_profiles", []) or [])
    supported_profiles = [name for name in requested_profiles if name in CAPABILITY_PROFILES]
    unsupported_profiles = [name for name in requested_profiles if name not in CAPABILITY_PROFILES]
    requested_methods = list(params.get("requires_methods", []) or [])
    supported_methods = [name for name in requested_methods if name in METHODS]
    unsupported_methods = [name for name in requested_methods if name not in METHODS]
    result: dict[str, Any] = {
        "requested_features": requested,
        "supported_features": supported,
        "unsupported_features": unsupported,
        "requested_profiles": requested_profiles,
        "supported_profiles": supported_profiles,
        "unsupported_profiles": unsupported_profiles,
        "requested_methods": requested_methods,
        "supported_methods": supported_methods,
        "unsupported_methods": unsupported_methods,
        "satisfied": not unsupported and not unsupported_profiles and not unsupported_methods,
    }
    if params.get("client"):
        result["client"] = params["client"]
    return result


def capabilities(params: dict[str, Any] | None = None) -> dict[str, Any]:
    params = params or {}
    features = capability_features()
    return {
        "protocol": "akbp-jsonl-tool-server",
        "version": "0.1-draft",
        "features": features,
        "negotiation": negotiation_result(params, features),
        "knowledge_capability": KNOWLEDGE_CAPABILITY,
        "schemas": {
            "request": REQUEST_SCHEMA,
            "response": RESPONSE_SCHEMA,
            "methods": METHODS_SCHEMA,
        },
        "runtime": {
            "transport": "jsonl-stdio",
            "default_path": ".",
            "max_request_bytes": MAX_REQUEST_BYTES,
            "max_request_id_length": MAX_REQUEST_ID_LENGTH,
            "max_request_id_abs_value": MAX_REQUEST_ID_ABS_VALUE,
            "max_error_output_bytes": MAX_ERROR_OUTPUT_BYTES,
            "hash_algorithms": ["sha256"],
            "supports_dry_run": True,
            "write_policy": "review-gated",
            "approval_field": "approved",
            "path_policy": "caller-supplied local path; empty paths, oversized paths, and control characters are rejected before dispatch",
            "param_length_policy": "string params are capped before CLI dispatch according to method schemas",
            "context_budget_policy": "akbp.context and akbp.session.start accept max_chars so adapters can request cited startup context without loading full memory artifacts into the prompt",
            "param_min_length_policy": "non-empty string params reject empty or whitespace-only values before CLI dispatch",
            "param_control_char_policy": "path-like, identifier, evidence, and entity string params reject NUL, newline, and carriage return before CLI dispatch",
            "param_array_policy": "evidence and entity arrays are capped for item count and per-item string length before CLI dispatch",
            "param_enum_policy": "claim type, source type, conformance level, and related enum params are checked against the public schemas before CLI dispatch",
            "param_numeric_range_policy": "limit, min_items, max_chars, and confidence params are checked against method schema bounds before CLI dispatch",
            "finite_numeric_param_policy": "numeric params are rejected when parser overflow would produce non-finite floats before CLI dispatch",
            "request_id_policy": "request ids must be finite strings or numbers; string ids are capped at 512 characters and reject NUL, newline, and carriage return; numeric ids are capped at the JavaScript safe integer range before dispatch",
            "cli_error_output_policy": "CLI error stdout and stderr are redacted first, then capped before being returned in structured error responses",
            "method_schema_parity_policy": "implemented methods, accepted params, and required params are checked against tool-methods.schema.json at server startup when schemas are present; installed single-module packages use the embedded runtime declarations as a fallback",
            "method_schema_runtime_errors": SCHEMA_RUNTIME_ERRORS,
        },
        "methods": {
            name: {
                **meta,
                "review_required": bool(meta.get("write")),
                **({"params_schema": ref} if (ref := method_schema_ref(name)) else {}),
            }
            for name, meta in METHODS.items()
        },
        "profiles": CAPABILITY_PROFILES,
        "profile_contracts": PROFILE_CONTRACTS,
        "examples": [
            {"id": "status-1", "method": "akbp.status", "path": "."},
            {"id": "doctor-1", "method": "akbp.doctor", "path": "."},
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
            {"id": "session-start-1", "method": "akbp.session.start", "path": ".", "params": {"task": "continue the release", "limit": 5, "max_chars": 4000}},
            {"id": "session-end-1", "method": "akbp.session.end", "path": ".", "dry_run": True, "params": {"transcript": "session-summary.md", "apply": True}},
        ],
    }


def build_argv(method: str, params: dict[str, Any]) -> list[str]:
    doctor_profile_args = {
        "startup_context": "startup-context",
        "read_only": "read-only",
        "reviewed_write": "reviewed-writes",
    }
    mapping = {
        "akbp.status": ["status", "--limit", str(params.get("limit", 5))],
        "akbp.doctor": ["doctor"],
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
        "akbp.session.start": ["context", params.get("task") or params.get("query") or "current task goals and constraints", "--limit", str(params.get("limit", 5))],
        "akbp.session.end": ["crystallize", params.get("transcript", "")],
    }
    argv = [str(a) for a in mapping[method] if a != ""]
    if method == "akbp.doctor" and params.get("profile"):
        argv.extend(["--profile", doctor_profile_args[str(params["profile"])]])
    if method in {"akbp.context", "akbp.session.start"} and "max_chars" in params:
        argv.extend(["--max-chars", str(params["max_chars"])])
    if method in {"akbp.context", "akbp.session.start"} and "min_items" in params:
        argv.extend(["--min-items", str(params["min_items"])])
    if method in {"akbp.context", "akbp.session.start"} and params.get("require_citations"):
        argv.append("--require-citations")
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
    if method in {"akbp.crystallize_session", "akbp.session.end"} and params.get("apply"):
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


def redact_argv(argv: list[str]) -> tuple[list[str], bool]:
    redacted = [akbp.redact_text(arg) for arg in argv]
    return redacted, redacted != argv


def truncate_text(value: str, max_bytes: int) -> tuple[str, bool]:
    encoded = value.encode("utf-8")
    if len(encoded) <= max_bytes:
        return value, False
    truncated = encoded[:max_bytes].decode("utf-8", errors="ignore").rstrip()
    return f"{truncated}\n[truncated]", True


def reject_json_constant(value: str) -> None:
    raise json.JSONDecodeError(f"invalid JSON constant: {value}", value, 0)


def parse_payload(stdout: str) -> Any:
    if not stdout.strip():
        return None
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return stdout


def request_id_errors(value: Any) -> list[str]:
    if not isinstance(value, (str, int, float)) or isinstance(value, bool):
        return ["id must be a finite string or number"]
    if isinstance(value, float) and not math.isfinite(value):
        return ["id must be a finite string or number"]
    if isinstance(value, (int, float)) and abs(value) > MAX_REQUEST_ID_ABS_VALUE:
        return [f"id numeric value must be between -{MAX_REQUEST_ID_ABS_VALUE} and {MAX_REQUEST_ID_ABS_VALUE}"]
    if isinstance(value, str):
        errors = []
        if len(value) > MAX_REQUEST_ID_LENGTH:
            errors.append(f"id must be at most {MAX_REQUEST_ID_LENGTH} characters")
        if has_control_char(value):
            errors.append("id must not contain control characters")
        return errors
    return []


def is_valid_request_id(value: Any) -> bool:
    return not request_id_errors(value)


def request_shape_errors(req: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    unknown_fields = sorted(name for name in req if name not in ALLOWED_REQUEST_FIELDS)
    if unknown_fields:
        errors.append("unknown request field(s): " + ", ".join(unknown_fields))
    if "id" not in req:
        errors.append("missing required field: id")
    else:
        errors.extend(request_id_errors(req.get("id")))
    if "method" not in req:
        errors.append("missing required field: method")
    elif not isinstance(req.get("method"), str) or not req.get("method", "").startswith("akbp."):
        errors.append("method must be an akbp.* string")
    if "path" in req and not isinstance(req.get("path"), str):
        errors.append("path must be a string")
    elif "path" in req:
        path = req.get("path", "")
        if not path.strip():
            errors.append("path must not be empty")
        if len(path) > 4096:
            errors.append("path must be 4096 characters or fewer")
        if any(char in path for char in ("\x00", "\n", "\r")):
            errors.append("path must not contain control characters")
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
CONFORMANCE_LEVELS = {"0", "1", "2", "3"}

CONTROL_CHAR_STRING_PARAMS = {
    "file",
    "locator",
    "source_id",
    "claim_id",
    "old_claim_id",
    "source_claim_id",
    "target_claim_id",
    "type",
    "claim_type",
    "level",
    "profile",
}


def has_control_char(value: str) -> bool:
    return any(char in value for char in ("\x00", "\n", "\r"))


NON_EMPTY_STRING_PARAMS = {
    "query",
    "task",
    "text",
    "locator",
    "file",
    "old_claim_id",
    "source_id",
    "source_claim_id",
    "target_claim_id",
    "transcript",
    "claim_id",
}


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
    "profile",
}


def is_finite_number(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    if isinstance(value, float) and not math.isfinite(value):
        return False
    return True


def param_type_errors(method: str, params: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for name in sorted(STRING_PARAMS.intersection(params)):
        value = params.get(name)
        if not isinstance(value, str):
            errors.append(f"{name} must be a string")
            continue
        if name in NON_EMPTY_STRING_PARAMS and name not in REQUIRED_PARAMS.get(method, ()) and not value.strip():
            errors.append(f"{name} must not be empty")
        max_length = PARAM_MAX_LENGTHS.get(name)
        if max_length is not None and len(value) > max_length:
            errors.append(f"{name} must be at most {max_length} characters")
        if name in CONTROL_CHAR_STRING_PARAMS and has_control_char(value):
            errors.append(f"{name} must not contain control characters")
    if "type" in params and method in {"akbp.remember", "akbp.supersede"} and params.get("type") not in CLAIM_TYPES:
        errors.append("type must be one of: " + ", ".join(sorted(CLAIM_TYPES)))
    if "type" in params and method in {"akbp.source.add", "akbp.ingest"} and params.get("type") not in SOURCE_TYPES:
        errors.append("type must be one of: " + ", ".join(sorted(SOURCE_TYPES)))
    if "claim_type" in params and method == "akbp.ingest" and params.get("claim_type") not in CLAIM_TYPES:
        errors.append("claim_type must be one of: " + ", ".join(sorted(CLAIM_TYPES)))
    if "level" in params and method == "akbp.conformance" and params.get("level") not in CONFORMANCE_LEVELS:
        errors.append("level must be one of: " + ", ".join(sorted(CONFORMANCE_LEVELS)))
    if "profile" in params and method == "akbp.doctor" and params.get("profile") not in {"startup_context", "read_only", "reviewed_write"}:
        errors.append("profile must be one of: read_only, reviewed_write, startup_context")
    if "client" in params:
        client = params.get("client")
        if not isinstance(client, str):
            errors.append("client must be a string")
        else:
            if len(client) > 128:
                errors.append("client must be at most 128 characters")
            if has_control_char(client):
                errors.append("client must not contain control characters")
    if "requires" in params:
        requires = params.get("requires")
        if not isinstance(requires, list):
            errors.append("requires must be an array")
        else:
            if len(requires) > 64:
                errors.append("requires must contain at most 64 items")
            for index, item in enumerate(requires):
                if not isinstance(item, str):
                    errors.append("requires items must be strings")
                    break
                if not item.strip():
                    errors.append(f"requires[{index}] must not be empty")
                if len(item) > 128:
                    errors.append(f"requires[{index}] must be at most 128 characters")
                if has_control_char(item):
                    errors.append(f"requires[{index}] must not contain control characters")
    if "requires_profiles" in params:
        requires_profiles = params.get("requires_profiles")
        if not isinstance(requires_profiles, list):
            errors.append("requires_profiles must be an array")
        else:
            if len(requires_profiles) > 16:
                errors.append("requires_profiles must contain at most 16 items")
            for index, item in enumerate(requires_profiles):
                if not isinstance(item, str):
                    errors.append("requires_profiles items must be strings")
                    break
                if not item.strip():
                    errors.append(f"requires_profiles[{index}] must not be empty")
                if len(item) > 64:
                    errors.append(f"requires_profiles[{index}] must be at most 64 characters")
                if has_control_char(item):
                    errors.append(f"requires_profiles[{index}] must not contain control characters")
    if "requires_methods" in params:
        requires_methods = params.get("requires_methods")
        if not isinstance(requires_methods, list):
            errors.append("requires_methods must be an array")
        else:
            if len(requires_methods) > 64:
                errors.append("requires_methods must contain at most 64 items")
            for index, item in enumerate(requires_methods):
                if not isinstance(item, str):
                    errors.append("requires_methods items must be strings")
                    break
                if not item.strip():
                    errors.append(f"requires_methods[{index}] must not be empty")
                if len(item) > 128:
                    errors.append(f"requires_methods[{index}] must be at most 128 characters")
                if has_control_char(item):
                    errors.append(f"requires_methods[{index}] must not contain control characters")
    if "dry_run" in params and not isinstance(params.get("dry_run"), bool):
        errors.append("dry_run must be a boolean")
    if "limit" in params:
        limit = params.get("limit")
        if not isinstance(limit, int) or isinstance(limit, bool):
            errors.append("limit must be an integer")
        elif limit < 1 or limit > 100:
            errors.append("limit must be between 1 and 100")
    if "max_chars" in params:
        max_chars = params.get("max_chars")
        if not isinstance(max_chars, int) or isinstance(max_chars, bool):
            errors.append("max_chars must be an integer")
        elif max_chars < 1 or max_chars > 65536:
            errors.append("max_chars must be between 1 and 65536")
    if "min_items" in params:
        min_items = params.get("min_items")
        if not isinstance(min_items, int) or isinstance(min_items, bool):
            errors.append("min_items must be an integer")
        elif min_items < 0 or min_items > 100:
            errors.append("min_items must be between 0 and 100")
    if "confidence" in params:
        confidence = params.get("confidence")
        if not is_finite_number(confidence):
            errors.append("confidence must be a finite number")
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
    for list_name in ("evidence", "entity"):
        if list_name not in params:
            continue
        values = params.get(list_name)
        limits = PARAM_LIST_LIMITS[list_name]
        if not isinstance(values, list):
            errors.append(f"{list_name} must be an array")
            continue
        if len(values) > limits["max_items"]:
            errors.append(f"{list_name} must contain at most {limits['max_items']} items")
        for index, item in enumerate(values):
            if not isinstance(item, str):
                errors.append(f"{list_name} items must be strings")
                break
            if len(item) > limits["max_item_length"]:
                errors.append(f"{list_name}[{index}] must be at most {limits['max_item_length']} characters")
            if has_control_char(item):
                errors.append(f"{list_name}[{index}] must not contain control characters")
    if method in {"akbp.crystallize_session", "akbp.session.end"} and "apply" in params and not isinstance(params.get("apply"), bool):
        errors.append("apply must be a boolean")
    return errors


def handle(req: dict[str, Any]) -> dict[str, Any]:
    request_id = req.get("id") if is_valid_request_id(req.get("id")) else None
    shape_errors = request_shape_errors(req)
    if shape_errors:
        return invalid_request_response(request_id, shape_errors)

    method = req.get("method")
    path = str(req.get("path", "."))
    params = req["params"] if "params" in req else {}

    if method not in METHODS:
        return error_response(request_id, "unknown_method", f"unknown method: {method}", details={"available_methods": sorted(METHODS)})
    if SCHEMA_RUNTIME_ERRORS:
        return error_response(
            request_id,
            "internal_error",
            "tool method schema/runtime parity check failed",
            details={"errors": SCHEMA_RUNTIME_ERRORS},
        )
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

    if method == "akbp.capabilities":
        return {"id": request_id, "ok": True, "result": capabilities(params), "error": None}

    argv = build_argv(method, params)
    if dry_run and method == "akbp.ingest":
        code, stdout, stderr = run_cli(path, [*argv, "--dry-run"])
        if code != 0:
            return cli_error_response(request_id, method, code, stdout, stderr)
        result = parse_payload(stdout)
        if isinstance(result, dict):
            result.setdefault("review_required", True)
            result.setdefault("apply_instruction", "Repeat the same request without dry_run only after reviewing redaction status, extracted signals, claim ids, would_write paths, and approval or trusted local policy.")
        return {"id": request_id, "ok": True, "result": result, "error": None}

    if method == "akbp.session.start":
        code, stdout, stderr = run_cli(path, argv)
        if code != 0:
            return cli_error_response(request_id, method, code, stdout, stderr)
        task = params.get("task") or params.get("query") or "current task goals and constraints"
        return {
            "id": request_id,
            "ok": True,
            "result": {
                "session_id": akbp.stable_id("adapter_session", path, str(task)),
                "task": str(task),
                "context": parse_payload(stdout),
            },
            "error": None,
        }

    if dry_run and method in {"akbp.crystallize_session", "akbp.session.end"}:
        preview_argv = [arg for arg in argv if arg != "--apply"]
        code, stdout, stderr = run_cli(path, preview_argv)
        if code != 0:
            return cli_error_response(request_id, method, code, stdout, stderr)
        result = parse_payload(stdout)
        if isinstance(result, dict):
            result.setdefault("dry_run", True)
            result.setdefault("would_write", True)
            result.setdefault("review_required", True)
            result.setdefault("apply_instruction", "Review the extracted session summary, skipped claims, planned page path, and evidence before repeating with approved:true after approval and apply:true.")
        return {"id": request_id, "ok": True, "result": result, "error": None}

    if dry_run and method == "akbp.import_apply":
        code, stdout, stderr = run_cli(path, [*argv, "--dry-run"])
        if code != 0 and not stdout.strip():
            return cli_error_response(request_id, method, code, stdout, stderr)
        result = parse_payload(stdout)
        if isinstance(result, dict):
            result.setdefault("review_required", True)
            result.setdefault("apply_instruction", "Repeat the same request with approved:true only after reviewing import-check output and dry-run would_write ids.")
        return {"id": request_id, "ok": True, "result": result, "error": None}

    if dry_run and method in WRITE_METHODS:
        safe_argv, redacted = redact_argv(argv)
        return {
            "id": request_id,
            "ok": True,
            "result": {
                "dry_run": True,
                "method": method,
                "path": path,
                "argv": safe_argv,
                "redacted": redacted,
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
    if method in {"akbp.export_check", "akbp.import_check", "akbp.import_apply", "akbp.source.verify"} and stdout.strip():
        return {"id": request_id, "ok": True, "result": parse_payload(stdout), "error": None}
    if code != 0:
        return cli_error_response(request_id, method, code, stdout, stderr)
    return {"id": request_id, "ok": True, "result": parse_payload(stdout), "error": None}


def main() -> int:
    for line in sys.stdin:
        if len(line.encode("utf-8")) > MAX_REQUEST_BYTES:
            print(
                json.dumps(
                    error_response(
                        None,
                        "invalid_request",
                        "request line exceeds max_request_bytes",
                        details={"errors": [f"request line exceeds max_request_bytes ({MAX_REQUEST_BYTES})"], "schema": REQUEST_SCHEMA},
                    ),
                    ensure_ascii=False,
                    allow_nan=False,
                ),
                flush=True,
            )
            continue
        line = line.strip()
        if not line:
            continue
        request_id = None
        try:
            req = json.loads(line, parse_constant=reject_json_constant)
            if not isinstance(req, dict):
                print(
                    json.dumps(
                        invalid_request_response(None, ["request must be a JSON object"], "request must be a JSON object"),
                        ensure_ascii=False,
                        allow_nan=False,
                    ),
                    flush=True,
                )
                continue
            request_id = req.get("id") if is_valid_request_id(req.get("id")) else None
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
        print(json.dumps(res, ensure_ascii=False, allow_nan=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
