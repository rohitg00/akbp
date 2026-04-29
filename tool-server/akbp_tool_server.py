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


def run_cli(path: str, argv: list[str]) -> tuple[int, str, str]:
    out = io.StringIO()
    err = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = akbp.main(["--path", path, *argv])
    return int(code or 0), out.getvalue(), err.getvalue()


def handle(req: dict[str, Any]) -> dict[str, Any]:
    request_id = req.get("id")
    path = req.get("path", ".")
    method = req.get("method")
    params = req.get("params", {}) or {}
    mapping = {
        "akbp.status": ["status"],
        "akbp.query": ["query", params.get("query", ""), "--limit", str(params.get("limit", 10))],
        "akbp.context": ["context", params.get("task", ""), "--limit", str(params.get("limit", 10))],
        "akbp.remember": ["remember", params.get("text", ""), "--type", params.get("type", "observation")],
        "akbp.conformance": ["conformance", "--level", str(params.get("level", "0"))],
        "akbp.export": ["export"],
        "akbp.audit": ["audit", "--limit", str(params.get("limit", 20))],
        "akbp.cite": ["cite", params.get("claim_id", "")],
        "akbp.source.add": ["source", "add", params.get("locator", ""), "--type", params.get("type", "file")],
        "akbp.supersede": ["supersede", params.get("old_claim_id", ""), params.get("text", ""), "--type", params.get("type", "observation")],
        "akbp.contradict": ["contradict", params.get("source_claim_id", ""), params.get("target_claim_id", "")],
    }
    if method not in mapping:
        return {"id": request_id, "ok": False, "error": f"unknown method: {method}"}
    argv = [str(a) for a in mapping[method] if a != ""]
    for evidence in params.get("evidence", []) or []:
        if method in {"akbp.remember", "akbp.source.add", "akbp.supersede", "akbp.contradict"}:
            argv.extend(["--evidence", str(evidence)])
    for entity in params.get("entity", []) or []:
        if method in {"akbp.remember", "akbp.supersede"}:
            argv.extend(["--entity", str(entity)])
    if method == "akbp.source.add" and params.get("title"):
        argv.extend(["--title", str(params["title"])])
    code, stdout, stderr = run_cli(path, argv)
    try:
        payload = json.loads(stdout) if stdout.strip() else None
    except json.JSONDecodeError:
        payload = stdout
    return {"id": request_id, "ok": code == 0, "result": payload, "error": stderr.strip() or None}


def main() -> int:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            res = handle(req)
        except Exception as exc:  # pragma: no cover - defensive server boundary
            res = {"id": None, "ok": False, "error": str(exc)}
        print(json.dumps(res, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
