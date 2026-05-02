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
    "akbp.index",
    "akbp.supersede",
    "akbp.contradict",
}

METHODS: dict[str, dict[str, Any]] = {
    "akbp.capabilities": {"write": False, "params": []},
    "akbp.status": {"write": False, "params": []},
    "akbp.query": {"write": False, "params": ["query", "limit"]},
    "akbp.context": {"write": False, "params": ["task", "limit"]},
    "akbp.index": {"write": True, "params": ["incremental"]},
    "akbp.search": {"write": False, "params": ["query", "limit"]},
    "akbp.remember": {"write": True, "params": ["text", "type", "evidence", "entity"]},
    "akbp.conformance": {"write": False, "params": ["level"]},
    "akbp.export": {"write": False, "params": []},
    "akbp.audit": {"write": False, "params": ["limit"]},
    "akbp.cite": {"write": False, "params": ["claim_id"]},
    "akbp.source.add": {"write": True, "params": ["locator", "type", "title", "evidence"]},
    "akbp.ingest": {"write": True, "params": ["file", "type", "title", "claim", "claim_type", "confidence", "entity"]},
    "akbp.supersede": {"write": True, "params": ["old_claim_id", "text", "type", "evidence", "entity"]},
    "akbp.contradict": {"write": True, "params": ["source_claim_id", "target_claim_id", "evidence"]},
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
            "jsonl_transport": True,
        },
        "schemas": {
            "request": REQUEST_SCHEMA,
            "response": RESPONSE_SCHEMA,
            "methods": METHODS_SCHEMA,
        },
        "methods": {
            name: {**meta, **({"params_schema": ref} if (ref := method_schema_ref(name)) else {})}
            for name, meta in METHODS.items()
        },
        "examples": [
            {"id": "status-1", "method": "akbp.status", "path": "."},
            {"id": "query-1", "method": "akbp.query", "path": ".", "params": {"query": "deployment", "limit": 5}},
            {"id": "search-1", "method": "akbp.search", "path": ".", "params": {"query": "deployment", "limit": 5}},
            {"id": "safe-write-1", "method": "akbp.remember", "path": ".", "dry_run": True, "params": {"text": "Agents need rollback paths"}},
            {"id": "ingest-1", "method": "akbp.ingest", "path": ".", "dry_run": True, "params": {"file": "notes.md", "claim": "The project ships small verified batches"}},
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
        "akbp.audit": ["audit", "--limit", str(params.get("limit", 20))],
        "akbp.cite": ["cite", params.get("claim_id", "")],
        "akbp.source.add": ["source", "add", params.get("locator", ""), "--type", params.get("type", "file")],
        "akbp.ingest": ["ingest", params.get("file", ""), "--type", params.get("type", "file")],
        "akbp.supersede": ["supersede", params.get("old_claim_id", ""), params.get("text", ""), "--type", params.get("type", "observation")],
        "akbp.contradict": ["contradict", params.get("source_claim_id", ""), params.get("target_claim_id", "")],
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
    if method in {"akbp.source.add", "akbp.ingest"} and params.get("title"):
        argv.extend(["--title", str(params["title"])])
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


def handle(req: dict[str, Any]) -> dict[str, Any]:
    request_id = req.get("id")
    method = req.get("method")
    path = str(req.get("path", "."))
    params = req.get("params", {}) or {}
    dry_run = bool(req.get("dry_run") or params.get("dry_run"))

    if not isinstance(params, dict):
        return error_response(request_id, "invalid_params", "params must be an object")
    if method == "akbp.capabilities":
        return {"id": request_id, "ok": True, "result": capabilities(), "error": None}
    if method not in METHODS:
        return error_response(request_id, "unknown_method", f"unknown method: {method}", details={"available_methods": sorted(METHODS)})

    argv = build_argv(method, params)
    if dry_run and method in WRITE_METHODS:
        return {
            "id": request_id,
            "ok": True,
            "result": {"dry_run": True, "method": method, "path": path, "argv": argv, "would_write": True},
            "error": None,
        }

    code, stdout, stderr = run_cli(path, argv)
    if code != 0:
        return error_response(request_id, "cli_error", stderr.strip() or "AKBP command failed", details={"exit_code": code, "stdout": stdout})
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
            res = error_response(None, "invalid_json", str(exc))
        except Exception as exc:  # pragma: no cover - defensive server boundary
            res = error_response(request_id, "internal_error", str(exc))
        print(json.dumps(res, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
