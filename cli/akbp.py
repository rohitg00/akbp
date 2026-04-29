#!/usr/bin/env python3
"""AKBP reference CLI v0.1.

A small dependency-free implementation for Level 0/1 AKBP knowledge bases.
It writes portable markdown + JSONL artifacts. It is intentionally boring.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Iterable

UTC = dt.timezone.utc


def now_iso() -> str:
    return dt.datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def slugify(text: str, max_len: int = 80) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"^-+|-+$", "", text)
    return (text[:max_len].strip("-") or "item")


def stable_id(prefix: str, *parts: str) -> str:
    h = hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{h}"


def root(path: str | None = None) -> Path:
    return Path(path or os.getcwd()).resolve()


def ensure_dirs(base: Path) -> None:
    for rel in [
        ".akbp",
        "raw/sources",
        "wiki/entities",
        "wiki/concepts",
        "wiki/decisions",
        "wiki/workflows",
        "wiki/sessions",
        "claims",
        "graph",
        "indexes",
        "logs",
    ]:
        (base / rel).mkdir(parents=True, exist_ok=True)


def append_jsonl(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False, sort_keys=True) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        out.append(json.loads(line))
    return out


def audit(base: Path, event: str, data: dict[str, Any]) -> None:
    append_jsonl(base / ".akbp" / "audit.log.jsonl", {
        "id": stable_id("audit", event, now_iso(), json.dumps(data, sort_keys=True)),
        "event": event,
        "created_at": now_iso(),
        "data": data,
    })


def write_if_missing(path: Path, content: str) -> None:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def cmd_init(args: argparse.Namespace) -> int:
    base = root(args.path)
    ensure_dirs(base)
    write_if_missing(base / ".akbp" / "config.json", json.dumps({
        "version": "0.1",
        "name": base.name,
        "created_at": now_iso(),
        "retrieval_modes": ["index", "jsonl"],
    }, indent=2) + "\n")
    write_if_missing(base / "wiki" / "index.md", "# AKBP Index\n\nGenerated index for this knowledge base.\n\n")
    write_if_missing(base / "wiki" / "log.md", "# AKBP Log\n\nAppend-only human-readable operation log.\n\n")
    write_if_missing(base / "claims" / "claims.jsonl", "")
    write_if_missing(base / "graph" / "entities.jsonl", "")
    write_if_missing(base / "graph" / "relations.jsonl", "")
    audit(base, "init", {"path": str(base)})
    print(f"Initialized AKBP knowledge base at {base}")
    return 0


def add_log(base: Path, title: str, body: str) -> None:
    log = base / "wiki" / "log.md"
    with log.open("a", encoding="utf-8") as f:
        f.write(f"\n## [{now_iso()}] {title}\n\n{body}\n")


def cmd_remember(args: argparse.Namespace) -> int:
    base = root(args.path)
    ensure_dirs(base)
    text = args.text.strip()
    claim = {
        "id": stable_id("claim", text, args.type, args.scope),
        "text": text,
        "type": args.type,
        "status": "working",
        "confidence": args.confidence,
        "evidence": args.evidence or [],
        "entities": args.entity or [],
        "supersedes": [],
        "superseded_by": None,
        "scope": args.scope,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "last_confirmed_at": None,
    }
    append_jsonl(base / "claims" / "claims.jsonl", claim)
    add_log(base, "remember", f"- Claim: `{claim['id']}`\n- Text: {text}\n")
    audit(base, "remember", {"claim_id": claim["id"]})
    print(json.dumps(claim, indent=2, ensure_ascii=False))
    return 0


def score_query(query: str, text: str) -> int:
    q = {w for w in re.findall(r"[a-z0-9_/-]+", query.lower()) if len(w) > 1}
    t = re.findall(r"[a-z0-9_/-]+", text.lower())
    tf = {}
    for w in t:
        tf[w] = tf.get(w, 0) + 1
    return sum(tf.get(w, 0) for w in q)


def iter_markdown(base: Path) -> Iterable[tuple[str, str]]:
    for p in (base / "wiki").rglob("*.md"):
        yield str(p.relative_to(base)), p.read_text(encoding="utf-8", errors="ignore")


def cmd_query(args: argparse.Namespace) -> int:
    base = root(args.path)
    claims = read_jsonl(base / "claims" / "claims.jsonl")
    results = []
    for c in claims:
        score = score_query(args.query, c.get("text", ""))
        if score:
            results.append({"type": "claim", "score": score, "id": c["id"], "text": c["text"], "evidence": c.get("evidence", [])})
    for rel, text in iter_markdown(base):
        score = score_query(args.query, text)
        if score:
            snippet = re.sub(r"\s+", " ", text).strip()[:240]
            results.append({"type": "page", "score": score, "path": rel, "snippet": snippet})
    results.sort(key=lambda x: x["score"], reverse=True)
    out = {"query": args.query, "results": results[: args.limit]}
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


def session_summary(text: str) -> dict[str, list[str]]:
    lines = [l.strip("- *\t ") for l in text.splitlines() if l.strip()]
    decisions = [l for l in lines if re.search(r"\b(decided|decision|choose|chose|use|using|must|should)\b", l, re.I)]
    questions = [l for l in lines if "?" in l or re.search(r"\b(todo|open question|blocked|follow up)\b", l, re.I)]
    files = sorted(set(re.findall(r"(?:[\w.-]+/)+[\w.-]+", text)))[:50]
    return {"decisions": decisions[:20], "questions": questions[:20], "files": files}


def cmd_crystallize(args: argparse.Namespace) -> int:
    base = root(args.path)
    ensure_dirs(base)
    transcript_path = Path(args.transcript).resolve()
    text = transcript_path.read_text(encoding="utf-8", errors="ignore")
    summary = session_summary(text)
    sid = stable_id("session", str(transcript_path), text[:1000])
    page = base / "wiki" / "sessions" / f"{sid}.md"
    md = [f"# Session {sid}", "", f"Source: `{transcript_path}`", f"Created: {now_iso()}", ""]
    for section, items in summary.items():
        md.append(f"## {section.title()}")
        md.append("")
        if items:
            md.extend(f"- {i}" for i in items)
        else:
            md.append("- None detected")
        md.append("")
    if args.apply:
        page.write_text("\n".join(md), encoding="utf-8")
        for decision in summary["decisions"]:
            claim = {
                "id": stable_id("claim", decision, sid),
                "text": decision,
                "type": "decision",
                "status": "working",
                "confidence": 0.55,
                "evidence": [str(transcript_path)],
                "entities": [],
                "supersedes": [],
                "superseded_by": None,
                "scope": "project",
                "created_at": now_iso(),
                "updated_at": now_iso(),
                "last_confirmed_at": None,
            }
            append_jsonl(base / "claims" / "claims.jsonl", claim)
        add_log(base, "crystallize", f"- Session: `{sid}`\n- Source: `{transcript_path}`\n- Page: `{page.relative_to(base)}`\n")
        audit(base, "crystallize", {"session_id": sid, "source": str(transcript_path)})
    print(json.dumps({"session_id": sid, "apply": args.apply, "summary": summary, "page": str(page)}, indent=2))
    return 0


def cmd_lint(args: argparse.Namespace) -> int:
    base = root(args.path)
    issues = []
    required = ["wiki/index.md", "wiki/log.md", "claims/claims.jsonl", "graph/entities.jsonl", "graph/relations.jsonl"]
    for rel in required:
        if not (base / rel).exists():
            issues.append({"severity": "error", "message": f"missing {rel}"})
    for c in read_jsonl(base / "claims" / "claims.jsonl"):
        if not c.get("evidence"):
            issues.append({"severity": "warning", "message": f"claim {c.get('id')} has no evidence"})
    print(json.dumps({"ok": not any(i["severity"] == "error" for i in issues), "issues": issues}, indent=2))
    return 1 if any(i["severity"] == "error" for i in issues) else 0


def cmd_status(args: argparse.Namespace) -> int:
    base = root(args.path)
    claims = read_jsonl(base / "claims" / "claims.jsonl")
    pages = list((base / "wiki").rglob("*.md")) if (base / "wiki").exists() else []
    print(json.dumps({"path": str(base), "claims": len(claims), "pages": len(pages), "initialized": (base / ".akbp/config.json").exists()}, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="akbp", description="AKBP reference CLI")
    p.add_argument("--path", default=".", help="knowledge base path, default cwd")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init")
    s.set_defaults(func=cmd_init)

    s = sub.add_parser("remember")
    s.add_argument("text")
    s.add_argument("--type", default="observation", choices=["fact", "decision", "preference", "workflow", "observation", "question", "warning"])
    s.add_argument("--scope", default="project", choices=["private", "project", "team", "public"])
    s.add_argument("--confidence", default=0.5, type=float)
    s.add_argument("--evidence", action="append")
    s.add_argument("--entity", action="append")
    s.set_defaults(func=cmd_remember)

    s = sub.add_parser("query")
    s.add_argument("query")
    s.add_argument("--limit", type=int, default=10)
    s.set_defaults(func=cmd_query)

    s = sub.add_parser("crystallize")
    s.add_argument("transcript")
    s.add_argument("--apply", action="store_true")
    s.set_defaults(func=cmd_crystallize)

    s = sub.add_parser("lint")
    s.set_defaults(func=cmd_lint)

    s = sub.add_parser("status")
    s.set_defaults(func=cmd_status)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
