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


def file_hash(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


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



def default_card(base: Path) -> dict[str, Any]:
    return {
        "schema_version": "0.1-draft",
        "name": base.name,
        "description": "AKBP knowledge base",
        "root": ".",
        "artifacts": {
            "wiki": "wiki/",
            "claims": "claims/claims.jsonl",
            "entities": "graph/entities.jsonl",
            "relations": "graph/relations.jsonl",
            "sources": "raw/sources/",
            "audit": ".akbp/audit.log.jsonl",
        },
        "capabilities": {
            "remember": True,
            "retrieve": True,
            "crystallize": True,
            "supersede": False,
            "audit": True,
            "sync": False,
        },
        "retrieval": ["keyword"],
        "transports": ["cli"],
        "privacy": {
            "default_scope": "project",
            "secret_redaction": "required",
        },
    }


def default_akbp_md(base: Path) -> str:
    return f"""# AKBP

This repository contains an AKBP-compatible knowledge base.

## Purpose

Describe what durable knowledge belongs here and who should use it.

## Agent instructions

- Read `akbp.json` before writing knowledge.
- Store durable claims in `claims/claims.jsonl`.
- Store human-readable synthesis in `wiki/`.
- Preserve evidence for claims whenever possible.
- Do not store secrets, credentials, tokens, cookies, or private keys.
- Prefer updating existing pages over creating duplicate pages.

## Layout

```text
wiki/                human-readable compiled knowledge
claims/claims.jsonl  atomic durable claims
graph/               entities and relations
raw/sources/         immutable source material
.akbp/               local engine state and audit logs
```
"""

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




def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def load_claims(base: Path) -> list[dict[str, Any]]:
    return read_jsonl(base / "claims" / "claims.jsonl")


def load_sources(base: Path) -> list[dict[str, Any]]:
    return read_jsonl(base / "raw" / "sources" / "sources.jsonl")


def known_evidence_ids(base: Path) -> set[str]:
    ids = {s.get("id") for s in load_sources(base) if s.get("id")}
    # Paths are still allowed for Level 1 compatibility, but source IDs are preferred.
    return {str(i) for i in ids}


def claim_required_fields() -> list[str]:
    return ["id", "text", "status", "confidence", "evidence", "created_at"]


def validate_claim_shape(claim: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in claim_required_fields():
        if field not in claim:
            errors.append(f"claim missing {field}")
    if not isinstance(claim.get("id", ""), str) or not claim.get("id"):
        errors.append("claim id must be a non-empty string")
    if not isinstance(claim.get("text", ""), str) or not claim.get("text"):
        errors.append("claim text must be a non-empty string")
    if claim.get("status") not in {"working", "actionable", "stable", "contested", "superseded", "archived", "redacted"}:
        errors.append(f"claim {claim.get('id')} has invalid status")
    confidence = claim.get("confidence")
    if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        errors.append(f"claim {claim.get('id')} has invalid confidence")
    if not isinstance(claim.get("evidence"), list):
        errors.append(f"claim {claim.get('id')} evidence must be a list")
    return errors

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
    card = default_card(base)
    write_if_missing(base / "akbp.json", json.dumps(card, indent=2) + "\n")
    write_if_missing(base / "AKBP.md", default_akbp_md(base))
    write_if_missing(base / ".akbp" / "config.json", json.dumps({
        "version": "0.1",
        "name": base.name,
        "created_at": now_iso(),
        "card": "akbp.json",
        "retrieval_modes": ["keyword", "jsonl"],
    }, indent=2) + "\n")
    write_if_missing(base / "wiki" / "index.md", "# AKBP Index\n\nGenerated index for this knowledge base.\n\n")
    write_if_missing(base / "wiki" / "log.md", "# AKBP Log\n\nAppend-only human-readable operation log.\n\n")
    write_if_missing(base / "claims" / "claims.jsonl", "")
    write_if_missing(base / "raw" / "sources" / "sources.jsonl", "")
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


def collect_results(base: Path, query: str, limit: int) -> list[dict[str, Any]]:
    claims = read_jsonl(base / "claims" / "claims.jsonl")
    results: list[dict[str, Any]] = []
    for c in claims:
        score = score_query(query, c.get("text", ""))
        if score:
            results.append({"type": "claim", "score": score, "id": c["id"], "text": c["text"], "evidence": c.get("evidence", [])})
    for rel, text in iter_markdown(base):
        score = score_query(query, text)
        if score:
            snippet = re.sub(r"\s+", " ", text).strip()[:240]
            results.append({"type": "page", "score": score, "path": rel, "snippet": snippet})
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]


def cmd_query(args: argparse.Namespace) -> int:
    base = root(args.path)
    out = {"query": args.query, "results": collect_results(base, args.query, args.limit)}
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


def result_to_context_item(result: dict[str, Any]) -> dict[str, Any]:
    if result["type"] == "claim":
        return {
            "id": result["id"],
            "type": "claim",
            "summary": result["text"],
            "score": result["score"],
            "citations": result.get("evidence", []),
            "freshness": "unknown",
        }
    return {
        "id": result["path"],
        "type": "page",
        "summary": result["snippet"],
        "score": result["score"],
        "citations": [result["path"]],
        "freshness": "unknown",
    }


def cmd_context(args: argparse.Namespace) -> int:
    base = root(args.path)
    results = collect_results(base, args.task, args.limit)
    pack = {
        "query": args.task,
        "generated_at": now_iso(),
        "items": [result_to_context_item(r) for r in results],
        "warnings": [] if results else ["No matching AKBP context found."],
    }
    if args.markdown:
        print(f"# AKBP Context Pack\n\nQuery: {pack['query']}\nGenerated: {pack['generated_at']}\n")
        for item in pack["items"]:
            print(f"## {item['type']}: {item['id']}\n")
            print(item["summary"] + "\n")
            if item["citations"]:
                print("Citations: " + ", ".join(item["citations"]) + "\n")
        for warning in pack["warnings"]:
            print(f"> Warning: {warning}")
    else:
        print(json.dumps(pack, indent=2, ensure_ascii=False))
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



def check_level_0(base: Path) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    required = ["AKBP.md", "akbp.json", "wiki/index.md", "claims/claims.jsonl", "graph/entities.jsonl", "graph/relations.jsonl"]
    for rel in required:
        if not (base / rel).exists():
            issues.append({"severity": "error", "message": f"missing {rel}"})
    card_path = base / "akbp.json"
    if card_path.exists():
        try:
            card = json.loads(card_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            issues.append({"severity": "error", "message": f"invalid akbp.json: {exc}"})
        else:
            for field in ["schema_version", "name", "root", "artifacts", "capabilities"]:
                if field not in card:
                    issues.append({"severity": "error", "message": f"akbp.json missing {field}"})
            if not isinstance(card.get("artifacts"), dict):
                issues.append({"severity": "error", "message": "akbp.json artifacts must be an object"})
            if not isinstance(card.get("capabilities"), dict):
                issues.append({"severity": "error", "message": "akbp.json capabilities must be an object"})
            for artifact in ["wiki", "claims", "entities", "relations", "sources"]:
                if artifact not in card.get("artifacts", {}):
                    issues.append({"severity": "error", "message": f"akbp.json artifacts missing {artifact}"})
            for capability in ["remember", "retrieve", "crystallize", "audit"]:
                if capability not in card.get("capabilities", {}):
                    issues.append({"severity": "error", "message": f"akbp.json capabilities missing {capability}"})
    entrypoint = base / "AKBP.md"
    if entrypoint.exists() and not entrypoint.read_text(encoding="utf-8", errors="ignore").startswith("# "):
        issues.append({"severity": "error", "message": "AKBP.md must start with a level-one heading"})
    return issues


def check_level_1(base: Path) -> list[dict[str, str]]:
    issues = check_level_0(base)
    seen: set[str] = set()
    for claim in load_claims(base):
        cid = claim.get("id", "<missing>")
        if cid in seen:
            issues.append({"severity": "error", "message": f"duplicate claim id {cid}"})
        seen.add(cid)
        for err in validate_claim_shape(claim):
            issues.append({"severity": "error", "message": err})
        if not claim.get("evidence") and claim.get("status") not in {"working", "redacted"}:
            issues.append({"severity": "error", "message": f"claim {cid} requires evidence unless working or redacted"})
        for ev in claim.get("evidence", []):
            if not isinstance(ev, str) or not ev.strip():
                issues.append({"severity": "error", "message": f"claim {cid} has invalid evidence reference"})
    return issues




def check_level_2(base: Path) -> list[dict[str, str]]:
    issues = check_level_1(base)
    # Level 2 is the retrieval contract: a conforming KB must be queryable and return context packs.
    try:
        results = collect_results(base, "reference project decision", 5)
    except Exception as exc:  # pragma: no cover - defensive for third-party KBs
        issues.append({"severity": "error", "message": f"retrieval failed: {exc}"})
        return issues
    if load_claims(base) and not isinstance(results, list):
        issues.append({"severity": "error", "message": "retrieval must return a list"})
    for result in results:
        item = result_to_context_item(result)
        for field in ["id", "type", "summary"]:
            if field not in item:
                issues.append({"severity": "error", "message": f"context item missing {field}"})
    return issues

def conformance_issues(base: Path, level: str) -> dict[str, Any]:
    checks = {"0": check_level_0, "1": check_level_1, "2": check_level_2}
    if level not in checks:
        return {
            "name": "Not implemented in reference CLI yet",
            "ok": False,
            "issues": [{"severity": "error", "message": f"conformance level {level} is not implemented yet"}],
        }
    issues = checks[level](base)
    names = {"0": "File convention", "1": "Structured claims and evidence", "2": "Retrieval and context packs"}
    return {
        "name": names[level],
        "ok": not any(i["severity"] == "error" for i in issues),
        "issues": issues,
    }


def cmd_conformance(args: argparse.Namespace) -> int:
    base = root(args.path)
    requested = args.level
    levels: dict[str, Any] = {}
    for level in [str(i) for i in range(int(requested) + 1)]:
        levels[level] = conformance_issues(base, level)
    result = {
        "path": str(base),
        "requested_level": requested,
        "ok": all(levels[level]["ok"] for level in levels),
        "levels": levels,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["ok"] else 1


def cmd_lint(args: argparse.Namespace) -> int:
    base = root(args.path)
    issues = check_level_0(base)
    for rel in ["wiki/log.md"]:
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
    sources = read_jsonl(base / "raw" / "sources" / "sources.jsonl")
    print(json.dumps({
        "path": str(base),
        "claims": len(claims),
        "sources": len(sources),
        "pages": len(pages),
        "initialized": (base / ".akbp/config.json").exists(),
        "card": (base / "akbp.json").exists(),
        "entrypoint": (base / "AKBP.md").exists(),
    }, indent=2))
    return 0




def cmd_audit(args: argparse.Namespace) -> int:
    base = root(args.path)
    events = read_jsonl(base / ".akbp" / "audit.log.jsonl")
    if args.event:
        events = [e for e in events if e.get("event") == args.event]
    events = events[-args.limit:]
    print(json.dumps({"events": events, "count": len(events)}, indent=2, ensure_ascii=False))
    return 0


def cmd_source_add(args: argparse.Namespace) -> int:
    base = root(args.path)
    ensure_dirs(base)
    locator = args.locator.strip()
    source_hash = args.hash
    if source_hash is None and args.type == "file":
        source_hash = file_hash((base / locator).resolve()) or file_hash(Path(locator).resolve())
    source = {
        "id": args.id or stable_id("source", args.type, locator),
        "type": args.type,
        "locator": locator,
        "title": args.title,
        "hash": source_hash,
        "immutable": not args.mutable,
        "scope": args.scope,
        "created_at": now_iso(),
        "metadata": {},
    }
    append_jsonl(base / "raw" / "sources" / "sources.jsonl", source)
    add_log(base, "source add", f"- Source: `{source['id']}`\n- Locator: {locator}\n")
    audit(base, "source_add", {"source_id": source["id"], "locator": locator})
    print(json.dumps(source, indent=2, ensure_ascii=False))
    return 0


def cmd_cite(args: argparse.Namespace) -> int:
    base = root(args.path)
    claims = load_claims(base)
    found = next((c for c in claims if c.get("id") == args.claim_id), None)
    if not found:
        print(json.dumps({"ok": False, "error": f"claim not found: {args.claim_id}"}, indent=2), file=sys.stderr)
        return 1
    print(json.dumps({
        "claim_id": found["id"],
        "text": found.get("text"),
        "evidence": found.get("evidence", []),
        "status": found.get("status"),
    }, indent=2, ensure_ascii=False))
    return 0


def cmd_supersede(args: argparse.Namespace) -> int:
    base = root(args.path)
    claims = load_claims(base)
    old = next((c for c in claims if c.get("id") == args.old_claim_id), None)
    if not old:
        print(json.dumps({"ok": False, "error": f"claim not found: {args.old_claim_id}"}, indent=2), file=sys.stderr)
        return 1
    new_claim = {
        "id": stable_id("claim", args.text, args.old_claim_id),
        "text": args.text.strip(),
        "type": args.type,
        "status": "working",
        "confidence": args.confidence,
        "evidence": args.evidence or [],
        "entities": args.entity or [],
        "supersedes": [args.old_claim_id],
        "superseded_by": None,
        "scope": args.scope,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "last_confirmed_at": None,
    }
    old["status"] = "superseded"
    old["superseded_by"] = new_claim["id"]
    old["updated_at"] = now_iso()
    claims.append(new_claim)
    write_jsonl(base / "claims" / "claims.jsonl", claims)
    add_log(base, "supersede", f"- Old claim: `{args.old_claim_id}`\n- New claim: `{new_claim['id']}`\n")
    audit(base, "supersede", {"old_claim_id": args.old_claim_id, "new_claim_id": new_claim["id"]})
    print(json.dumps(new_claim, indent=2, ensure_ascii=False))
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

    s = sub.add_parser("context")
    s.add_argument("task")
    s.add_argument("--limit", type=int, default=10)
    s.add_argument("--markdown", action="store_true")
    s.set_defaults(func=cmd_context)

    s = sub.add_parser("audit")
    s.add_argument("--limit", type=int, default=20)
    s.add_argument("--event")
    s.set_defaults(func=cmd_audit)

    s = sub.add_parser("source")
    source_sub = s.add_subparsers(dest="source_cmd", required=True)
    s_add = source_sub.add_parser("add")
    s_add.add_argument("locator")
    s_add.add_argument("--type", default="file", choices=["file", "url", "transcript", "message", "commit", "issue", "screenshot", "pdf", "audio", "video", "folder"])
    s_add.add_argument("--title")
    s_add.add_argument("--id")
    s_add.add_argument("--hash")
    s_add.add_argument("--mutable", action="store_true")
    s_add.add_argument("--scope", default="project", choices=["private", "project", "team", "public"])
    s_add.set_defaults(func=cmd_source_add)

    s = sub.add_parser("cite")
    s.add_argument("claim_id")
    s.set_defaults(func=cmd_cite)

    s = sub.add_parser("supersede")
    s.add_argument("old_claim_id")
    s.add_argument("text")
    s.add_argument("--type", default="observation", choices=["fact", "decision", "preference", "workflow", "observation", "question", "warning"])
    s.add_argument("--scope", default="project", choices=["private", "project", "team", "public"])
    s.add_argument("--confidence", default=0.5, type=float)
    s.add_argument("--evidence", action="append")
    s.add_argument("--entity", action="append")
    s.set_defaults(func=cmd_supersede)

    s = sub.add_parser("crystallize")
    s.add_argument("transcript")
    s.add_argument("--apply", action="store_true")
    s.set_defaults(func=cmd_crystallize)

    s = sub.add_parser("lint")
    s.set_defaults(func=cmd_lint)

    s = sub.add_parser("conformance")
    s.add_argument("--level", default="0", choices=["0", "1", "2", "3", "4", "5"])
    s.set_defaults(func=cmd_conformance)

    s = sub.add_parser("status")
    s.set_defaults(func=cmd_status)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
