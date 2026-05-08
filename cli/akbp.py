#!/usr/bin/env python3
"""AKBP reference CLI v0.1.

A small dependency-free implementation for Level 0/1 AKBP knowledge bases.
It writes portable markdown + JSONL artifacts. It is intentionally boring.
"""

from __future__ import annotations

import contextlib
import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sqlite3
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


def append_claim_once(base: Path, claim: dict[str, Any]) -> bool:
    claims_path = base / "claims" / "claims.jsonl"
    existing = {c.get("id") for c in read_jsonl(claims_path)}
    if claim["id"] in existing:
        return False
    append_jsonl(claims_path, claim)
    return True


def add_source_record(base: Path, locator: str, source_type: str = "file", title: str | None = None, scope: str = "project") -> dict[str, Any]:
    source_path = Path(locator)
    source = {
        "id": stable_id("source", source_type, locator),
        "type": source_type,
        "locator": locator,
        "title": title,
        "hash": file_hash(source_path) if source_path.exists() else None,
        "immutable": True,
        "scope": scope,
        "created_at": now_iso(),
        "metadata": {},
    }
    sources_path = base / "raw" / "sources" / "sources.jsonl"
    existing = {s.get("id") for s in read_jsonl(sources_path)}
    if source["id"] not in existing:
        append_jsonl(sources_path, source)
    return source


def load_claims(base: Path) -> list[dict[str, Any]]:
    return read_jsonl(base / "claims" / "claims.jsonl")


def load_sources(base: Path) -> list[dict[str, Any]]:
    return read_jsonl(base / "raw" / "sources" / "sources.jsonl")


def load_relations(base: Path) -> list[dict[str, Any]]:
    return read_jsonl(base / "graph" / "relations.jsonl")


def write_relations(base: Path, rows: list[dict[str, Any]]) -> None:
    write_jsonl(base / "graph" / "relations.jsonl", rows)


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
    auto_index_if_present(base)
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


def clean_line(line: str) -> str:
    return re.sub(r"\s+", " ", line.strip("- *\t >")).strip()


SESSION_SECTION_ALIASES = {
    "decisions": "decisions",
    "decision": "decisions",
    "actions": "actions",
    "action items": "actions",
    "action item": "actions",
    "todos": "actions",
    "todo": "actions",
    "next steps": "actions",
    "next step": "actions",
    "blockers": "blockers",
    "blocker": "blockers",
    "risks": "blockers",
    "risk": "blockers",
    "preferences": "preferences",
    "preference": "preferences",
    "rules": "preferences",
    "constraints": "preferences",
    "questions": "questions",
    "open questions": "questions",
    "question": "questions",
}


def normalize_session_line(line: str) -> str:
    line = re.sub(r"^\s*#{1,6}\s+", "", line)
    line = re.sub(r"^\s*(?:[-*]|\d+[.)])\s+", "", line)
    line = re.sub(r"^\s*\[[ xX]\]\s+", "", line)
    line = re.sub(r"^\s*(?:user|assistant|agent|system|developer|me|you|rohit)\s*:\s*", "", line, flags=re.I)
    line = re.sub(r"^\s*[A-Z][\w .-]{1,32}\s*:\s+", "", line)
    line = re.sub(
        r"^\s*(?:decision|decided|action item|action|todo|next step|blocker|blocked|preference|prefer|question|open question)\s*:\s*",
        "",
        line,
        flags=re.I,
    )
    return clean_line(line)


def session_section(line: str) -> str | None:
    heading = re.match(r"^\s*#{1,6}\s+(.+?)\s*$", line)
    label = heading.group(1) if heading else line.strip()
    label = re.sub(r"[:：]\s*$", "", label).strip().lower()
    return SESSION_SECTION_ALIASES.get(label)

def redact_text(text: str) -> str:
    patterns = [
        r"sk-[A-Za-z0-9_-]{8,}",
        r"xox[baprs]-[A-Za-z0-9-]{8,}",
        r"gh[pousr]_[A-Za-z0-9_]{16,}",
        r"AKIA[0-9A-Z]{12,}",
        r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*[^\s`'\"]+",
    ]
    redacted = text
    for pattern in patterns:
        redacted = re.sub(pattern, "[REDACTED]", redacted)
    return redacted


def imported_page_path(base: Path, source: Path) -> Path:
    return base / "wiki" / "imports" / f"{slugify(source.stem)}.md"


def heading_summary(text: str, limit: int = 12) -> list[str]:
    candidates = []
    for line in text.splitlines():
        cleaned = clean_line(line.lstrip("#"))
        if not cleaned:
            continue
        if line.lstrip().startswith("#") or re.search(r"\b(decision|decided|must|should|prefer|blocker|todo|next|source|claim)\b", cleaned, re.I):
            candidates.append(cleaned)
    return unique_keep_order(candidates, limit)


def cmd_ingest(args: argparse.Namespace) -> int:
    base = root(args.path)
    source_path = Path(args.file).resolve()
    if not source_path.exists() or not source_path.is_file():
        print(json.dumps({"ok": False, "error": f"file not found: {source_path}"}, indent=2), file=sys.stderr)
        return 1
    raw_text = source_path.read_text(encoding="utf-8", errors="ignore")
    safe_text = redact_text(raw_text)
    source_id = stable_id("source", args.type, str(source_path))
    page = imported_page_path(base, source_path)
    title = args.title or source_path.stem.replace("-", " ").replace("_", " ").title()
    summary_items = heading_summary(safe_text)
    raw_claim_text = args.claim.strip() if args.claim else ""
    safe_claim_text = redact_text(raw_claim_text) if raw_claim_text else ""
    claim_redacted = bool(raw_claim_text and raw_claim_text != safe_claim_text)
    claim_id = stable_id("claim", safe_claim_text, source_id) if safe_claim_text else None
    if args.dry_run:
        print(json.dumps({
            "ok": True,
            "dry_run": True,
            "source_id": source_id,
            "page": str(page.relative_to(base)),
            "signals": summary_items,
            "created_claims": [claim_id] if claim_id else [],
            "redacted": raw_text != safe_text or claim_redacted,
            "would_write": [
                "raw/sources/sources.jsonl",
                str(page.relative_to(base)),
                *(["claims/claims.jsonl"] if claim_id else []),
                "logs/log.md",
                "logs/audit.jsonl",
            ],
        }, indent=2, ensure_ascii=False))
        return 0

    ensure_dirs(base)
    source = add_source_record(base, str(source_path), args.type, args.title or source_path.name, args.scope)
    body = [
        f"# Imported Source: {title}",
        "",
        f"Source ID: `{source['id']}`",
        f"Original locator: `{source_path}`",
        f"Imported at: {now_iso()}",
        "",
        "## Extracted signals",
        "",
    ]
    body.extend(f"- {item}" for item in summary_items) if summary_items else body.append("- None detected")
    body.extend(["", "## Redacted content", "", safe_text.strip(), ""])
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text("\n".join(body), encoding="utf-8")
    created_claims = []
    if safe_claim_text:
        claim = {
            "id": stable_id("claim", safe_claim_text, source["id"]),
            "text": safe_claim_text,
            "type": args.claim_type,
            "status": "working",
            "confidence": args.confidence,
            "evidence": [source["id"]],
            "entities": args.entity or [],
            "supersedes": [],
            "superseded_by": None,
            "scope": args.scope,
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "last_confirmed_at": None,
        }
        if append_claim_once(base, claim):
            created_claims.append(claim["id"])
    add_log(base, "ingest", f"- Source: `{source['id']}`\n- Page: `{page.relative_to(base)}`\n- Claims: {len(created_claims)}\n")
    audit(base, "ingest", {"source_id": source["id"], "page": str(page.relative_to(base)), "claims_created": len(created_claims)})
    auto_index_if_present(base)
    print(json.dumps({
        "ok": True,
        "source_id": source["id"],
        "page": str(page.relative_to(base)),
        "signals": summary_items,
        "created_claims": created_claims,
        "redacted": raw_text != safe_text or claim_redacted,
    }, indent=2, ensure_ascii=False))
    return 0



def import_jsonl_objects(source: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for line_number, line in enumerate(source.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append({"line": line_number, "error": exc.msg})
            continue
        item_id = str(item.get("id") or f"line-{line_number}") if isinstance(item, dict) else f"line-{line_number}"
        kind = str(item.get("kind") or item.get("type") or "object") if isinstance(item, dict) else "object"
        raw = json.dumps(item, sort_keys=True, ensure_ascii=False)
        safe = redact_text(raw)
        if safe != raw:
            rejected.append({"id": item_id, "kind": kind, "line": line_number, "reason": "secret_like_value_redacted"})
        else:
            accepted.append({"id": item_id, "kind": kind, "line": line_number, "object": item})
    return accepted, rejected, errors


def public_import_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"id": item["id"], "kind": item["kind"], "line": item["line"], **({"reason": item["reason"]} if "reason" in item else {})} for item in items]


def normalize_import_object(item: dict[str, Any]) -> tuple[str | None, dict[str, Any] | None, str | None]:
    if not isinstance(item, dict):
        return None, None, "object must be a JSON object"
    kind = str(item.get("kind") or item.get("type") or "")
    if kind == "source":
        source = {
            "id": str(item.get("id") or stable_id("source", item.get("type", "file"), item.get("locator", ""))),
            "type": str(item.get("type") or "file"),
            "locator": str(item.get("locator") or item.get("id") or ""),
            "title": item.get("title"),
            "hash": item.get("hash"),
            "immutable": bool(item.get("immutable", True)),
            "scope": str(item.get("scope") or "project"),
            "created_at": str(item.get("created_at") or now_iso()),
            "metadata": item.get("metadata") if isinstance(item.get("metadata"), dict) else {},
        }
        if not source["locator"]:
            return kind, None, "source locator is required"
        return kind, source, None
    if kind == "claim":
        claim = {
            "id": str(item.get("id") or stable_id("claim", item.get("text", ""), item.get("type", "observation"), item.get("scope", "project"))),
            "text": str(item.get("text") or ""),
            "type": str(item.get("type") or "observation"),
            "status": str(item.get("status") or "working"),
            "confidence": item.get("confidence", 0.5),
            "evidence": item.get("evidence") if isinstance(item.get("evidence"), list) else [],
            "entities": item.get("entities") if isinstance(item.get("entities"), list) else [],
            "supersedes": item.get("supersedes") if isinstance(item.get("supersedes"), list) else [],
            "superseded_by": item.get("superseded_by"),
            "scope": str(item.get("scope") or "project"),
            "created_at": str(item.get("created_at") or now_iso()),
            "updated_at": str(item.get("updated_at") or now_iso()),
            "last_confirmed_at": item.get("last_confirmed_at"),
        }
        errors = validate_claim_shape(claim)
        if errors:
            return kind, None, "; ".join(errors)
        return kind, claim, None
    return kind or "object", None, "unsupported import kind"

def cmd_import_check(args: argparse.Namespace) -> int:
    source = Path(args.file).resolve()
    if not source.exists() or not source.is_file():
        print(json.dumps({"ok": False, "error": f"file not found: {source}"}, indent=2), file=sys.stderr)
        return 1
    accepted, rejected, errors = import_jsonl_objects(source)
    failed = bool(errors) or (bool(rejected) and bool(getattr(args, "fail_on_rejected", False)))
    print(json.dumps({
        "ok": not failed,
        "file": str(source),
        "checked": len(accepted) + len(rejected),
        "accepted_count": len(accepted),
        "rejected_count": len(rejected),
        "error_count": len(errors),
        "fail_on_rejected": bool(getattr(args, "fail_on_rejected", False)),
        "accepted": public_import_items(accepted),
        "rejected": public_import_items(rejected),
        "errors": errors,
    }, indent=2, ensure_ascii=False))
    return 1 if failed else 0




def cmd_import_apply(args: argparse.Namespace) -> int:
    base = root(args.path)
    ensure_dirs(base)
    source = Path(args.file).resolve()
    if not source.exists() or not source.is_file():
        print(json.dumps({"ok": False, "error": f"file not found: {source}"}, indent=2), file=sys.stderr)
        return 1
    accepted, rejected, errors = import_jsonl_objects(source)
    normalized: list[tuple[str, dict[str, Any], int]] = []
    for item in accepted:
        kind, record, error = normalize_import_object(item["object"])
        if error or record is None or kind is None:
            rejected.append({"id": item["id"], "kind": kind or item["kind"], "line": item["line"], "reason": error or "invalid_import_object"})
            continue
        normalized.append((kind, record, item["line"]))
    if errors or rejected:
        result = {
            "ok": False,
            "file": str(source),
            "dry_run": bool(args.dry_run),
            "applied": False,
            "checked": len(accepted) + len(rejected),
            "accepted_count": len(normalized),
            "rejected_count": len(rejected),
            "error_count": len(errors),
            "would_write": {
                "sources": [],
                "claims": [],
            },
            "skipped_existing": {
                "sources": [],
                "claims": [],
            },
            "accepted": [
                {"id": record["id"], "kind": kind, "line": line}
                for kind, record, line in normalized
            ],
            "rejected": public_import_items(rejected),
            "errors": errors,
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 1
    sources = [record for kind, record, _line in normalized if kind == "source"]
    claims = [record for kind, record, _line in normalized if kind == "claim"]
    source_existing = {item.get("id") for item in load_sources(base)}
    claim_existing = {item.get("id") for item in load_claims(base)}
    source_new = [item for item in sources if item.get("id") not in source_existing]
    claim_new = [item for item in claims if item.get("id") not in claim_existing]
    result = {
        "ok": True,
        "file": str(source),
        "dry_run": bool(args.dry_run),
        "applied": False,
        "checked": len(accepted),
        "accepted_count": len(normalized),
        "rejected_count": 0,
        "error_count": 0,
        "would_write": {
            "sources": [item["id"] for item in source_new],
            "claims": [item["id"] for item in claim_new],
        },
        "skipped_existing": {
            "sources": [item["id"] for item in sources if item.get("id") in source_existing],
            "claims": [item["id"] for item in claims if item.get("id") in claim_existing],
        },
    }
    if args.dry_run:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    if not args.approved:
        result["ok"] = False
        result["review_required"] = True
        result["apply_instruction"] = "Repeat with --approved only after reviewing import-check output and dry-run would_write ids."
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 1
    for item in source_new:
        append_jsonl(base / "raw" / "sources" / "sources.jsonl", item)
    for item in claim_new:
        append_jsonl(base / "claims" / "claims.jsonl", item)
    add_log(base, "import apply", f"- Sources: {len(source_new)}\n- Claims: {len(claim_new)}\n")
    audit(base, "import_apply", {"file": str(source), "sources": [item["id"] for item in source_new], "claims": [item["id"] for item in claim_new]})
    auto_index_if_present(base)
    result["applied"] = True
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def unique_keep_order(items: Iterable[str], limit: int = 20) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        cleaned = clean_line(item)
        if not cleaned or cleaned.lower() in seen:
            continue
        seen.add(cleaned.lower())
        out.append(cleaned)
        if len(out) >= limit:
            break
    return out


def session_summary(text: str) -> dict[str, list[str]]:
    section_items: dict[str, list[str]] = {name: [] for name in ["decisions", "actions", "blockers", "preferences", "questions"]}
    current_section: str | None = None
    lines: list[str] = []

    for raw in text.splitlines():
        if not clean_line(raw):
            continue
        detected_section = session_section(raw)
        is_heading = raw.lstrip().startswith("#") or bool(re.match(r"^\s*\w[\w -]{0,40}:\s*$", raw))
        if detected_section and is_heading:
            current_section = detected_section
            continue
        normalized = normalize_session_line(raw)
        if not normalized:
            continue
        lines.append(normalized)
        if current_section and (re.match(r"^\s*(?:[-*]|\d+[.)]|\[[ xX]\])", raw) or ":" in raw):
            section_items[current_section].append(normalized)

    decisions = unique_keep_order(
        list(section_items["decisions"]) + [l for l in lines
        if re.search(r"\b(decided|decision|choose|chose|use|using|must|should|standardize|require|requires)\b", l, re.I)
        ]
    )
    actions = unique_keep_order(
        list(section_items["actions"]) + [l for l in lines
        if re.search(r"\b(todo|next|follow up|follow-up|ship|implement|add|fix|update|wire|review)\b", l, re.I)
        ]
    )
    blockers = unique_keep_order(
        list(section_items["blockers"]) + [l for l in lines
        if re.search(r"\b(blocked|blocker|failed|failing|error|cannot|can't|missing|needs approval|requires approval)\b", l, re.I)
        ]
    )
    preferences = unique_keep_order(
        list(section_items["preferences"]) + [l for l in lines
        if re.search(r"\b(prefer|preference|do not|don't|never|always|avoid|keep|must not)\b", l, re.I)
        ]
    )
    questions = unique_keep_order(
        list(section_items["questions"]) + [l for l in lines
        if "?" in l or re.search(r"\b(open question|question)\b", l, re.I)
        ]
    )
    files = sorted(set(re.findall(r"(?:[\w.-]+/)+[\w.-]+", text)))[:50]
    return {
        "decisions": decisions,
        "actions": actions,
        "blockers": blockers,
        "preferences": preferences,
        "questions": questions,
        "files": files,
    }


def summary_claim_type(section: str) -> str:
    return {
        "decisions": "decision",
        "actions": "observation",
        "blockers": "warning",
        "preferences": "preference",
        "questions": "question",
    }.get(section, "observation")


def cmd_crystallize(args: argparse.Namespace) -> int:
    base = root(args.path)
    ensure_dirs(base)
    transcript_path = Path(args.transcript).resolve()
    text = transcript_path.read_text(encoding="utf-8", errors="ignore")
    summary = session_summary(text)
    sid = stable_id("session", str(transcript_path), text[:1000])
    page = base / "wiki" / "sessions" / f"{sid}.md"
    source = add_source_record(base, str(transcript_path), "transcript", transcript_path.name) if args.apply else None
    evidence = [source["id"]] if source else [str(transcript_path)]
    md = [f"# Session {sid}", "", f"Source: `{transcript_path}`", f"Created: {now_iso()}", ""]
    for section, items in summary.items():
        md.append(f"## {section.title()}")
        md.append("")
        if items:
            md.extend(f"- {i}" for i in items)
        else:
            md.append("- None detected")
        md.append("")
    created_claims: list[str] = []
    skipped_claims: list[str] = []
    if args.apply:
        page.write_text("\n".join(md), encoding="utf-8")
        for section in ["decisions", "actions", "blockers", "preferences", "questions"]:
            for item in summary[section]:
                claim = {
                    "id": stable_id("claim", section, item, sid),
                    "text": item,
                    "type": summary_claim_type(section),
                    "status": "working",
                    "confidence": 0.55,
                    "evidence": evidence,
                    "entities": [],
                    "supersedes": [],
                    "superseded_by": None,
                    "scope": "project",
                    "created_at": now_iso(),
                    "updated_at": now_iso(),
                    "last_confirmed_at": None,
                }
                if append_claim_once(base, claim):
                    created_claims.append(claim["id"])
                else:
                    skipped_claims.append(claim["id"])
        add_log(base, "crystallize", f"- Session: `{sid}`\n- Source: `{transcript_path}`\n- Page: `{page.relative_to(base)}`\n- Claims: {len(created_claims)} created, {len(skipped_claims)} skipped\n")
        audit(base, "crystallize", {"session_id": sid, "source": str(transcript_path), "claims_created": len(created_claims)})
        auto_index_if_present(base)
    print(json.dumps({
        "session_id": sid,
        "apply": args.apply,
        "summary": summary,
        "page": str(page),
        "source_id": source["id"] if source else None,
        "created_claims": created_claims,
        "skipped_claims": skipped_claims,
    }, indent=2))
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

def check_level_3(base: Path) -> list[dict[str, str]]:
    issues = check_level_2(base)
    claim_ids = {c.get("id") for c in load_claims(base)}
    for relation in load_relations(base):
        rid = relation.get("id", "<missing>")
        for field in ["id", "source", "relation", "target", "confidence", "evidence", "created_at"]:
            if field not in relation:
                issues.append({"severity": "error", "message": f"relation {rid} missing {field}"})
        if relation.get("relation") not in {"uses", "depends_on", "contradicts", "supersedes", "supports", "caused_by", "owned_by", "derived_from", "similar_to", "blocks", "implements", "references"}:
            issues.append({"severity": "error", "message": f"relation {rid} has invalid type"})
        confidence = relation.get("confidence")
        if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
            issues.append({"severity": "error", "message": f"relation {rid} has invalid confidence"})
        if relation.get("relation") in {"contradicts", "supersedes", "supports"}:
            if relation.get("source") not in claim_ids:
                issues.append({"severity": "error", "message": f"relation {rid} source claim does not exist"})
            if relation.get("target") not in claim_ids:
                issues.append({"severity": "error", "message": f"relation {rid} target claim does not exist"})
    return issues


def conformance_issues(base: Path, level: str) -> dict[str, Any]:
    checks = {"0": check_level_0, "1": check_level_1, "2": check_level_2, "3": check_level_3}
    if level not in checks:
        return {
            "name": "Not implemented in reference CLI yet",
            "ok": False,
            "issues": [{"severity": "error", "message": f"conformance level {level} is not implemented yet"}],
        }
    issues = checks[level](base)
    names = {"0": "File convention", "1": "Structured claims and evidence", "2": "Retrieval and context packs", "3": "Lifecycle relations"}
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




def index_documents(base: Path) -> list[dict[str, str]]:
    docs: list[dict[str, str]] = []
    for claim in load_claims(base):
        cid = str(claim.get("id", ""))
        text = str(claim.get("text", ""))
        docs.append({
            "doc_key": f"claim:{cid}",
            "kind": "claim",
            "object_id": cid,
            "path": "claims/claims.jsonl",
            "text": text,
            "digest": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        })
    for rel, text in iter_markdown(base):
        docs.append({
            "doc_key": f"page:{rel}",
            "kind": "page",
            "object_id": rel,
            "path": rel,
            "text": text,
            "digest": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        })
    return docs


def ensure_search_tables(con: sqlite3.Connection) -> None:
    con.execute("CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(kind, object_id, path, text)")
    con.execute("CREATE TABLE IF NOT EXISTS search_meta (doc_key TEXT PRIMARY KEY, kind TEXT NOT NULL, object_id TEXT NOT NULL, path TEXT NOT NULL, digest TEXT NOT NULL, rowid INTEGER NOT NULL)")


def index_base(base: Path, *, incremental: bool) -> dict[str, Any]:
    db_path = base / ".akbp" / "state.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    docs = index_documents(base)
    con = sqlite3.connect(db_path)
    rows = indexed = skipped = removed = 0
    indexed_keys: list[str] = []
    skipped_keys: list[str] = []
    removed_keys: list[str] = []
    try:
        ensure_search_tables(con)
        if not incremental:
            con.execute("DELETE FROM search_index")
            con.execute("DELETE FROM search_meta")
        existing = {row[0]: {"digest": row[1], "rowid": row[2]} for row in con.execute("SELECT doc_key, digest, rowid FROM search_meta")}
        wanted = {doc["doc_key"] for doc in docs}
        for doc_key, meta in existing.items():
            if doc_key not in wanted:
                con.execute("DELETE FROM search_index WHERE rowid = ?", (meta["rowid"],))
                con.execute("DELETE FROM search_meta WHERE doc_key = ?", (doc_key,))
                removed += 1
                removed_keys.append(doc_key)
        for doc in docs:
            old = existing.get(doc["doc_key"])
            if incremental and old and old["digest"] == doc["digest"]:
                skipped += 1
                skipped_keys.append(doc["doc_key"])
                continue
            if old:
                con.execute("DELETE FROM search_index WHERE rowid = ?", (old["rowid"],))
            cur = con.execute("INSERT INTO search_index(kind, object_id, path, text) VALUES (?, ?, ?, ?)", (doc["kind"], doc["object_id"], doc["path"], doc["text"]))
            con.execute(
                "INSERT OR REPLACE INTO search_meta(doc_key, kind, object_id, path, digest, rowid) VALUES (?, ?, ?, ?, ?, ?)",
                (doc["doc_key"], doc["kind"], doc["object_id"], doc["path"], doc["digest"], cur.lastrowid),
            )
            indexed += 1
            indexed_keys.append(doc["doc_key"])
        rows = len(docs)
        con.commit()
    finally:
        con.close()
    return {
        "ok": True,
        "db": str(db_path),
        "rows": rows,
        "indexed": indexed,
        "skipped": skipped,
        "removed": removed,
        "incremental": incremental,
        "indexed_keys": indexed_keys,
        "skipped_keys": skipped_keys,
        "removed_keys": removed_keys,
    }


def auto_index_if_present(base: Path) -> dict[str, Any] | None:
    if not (base / ".akbp" / "state.db").exists():
        return None
    return index_base(base, incremental=True)


def cmd_index(args: argparse.Namespace) -> int:
    base = root(args.path)
    result = index_base(base, incremental=args.incremental)
    audit(base, "index", {k: v for k, v in result.items() if k != "ok"})
    print(json.dumps(result, indent=2))
    return 0


def fts_term(token: str) -> str | None:
    token = token.strip()
    if not token:
        return None
    if token.startswith('"') and token.endswith('"'):
        phrase = re.sub(r'[^a-zA-Z0-9_/-]+', ' ', token[1:-1]).strip()
        return '"' + phrase.replace('"', '""') + '"' if phrase else None
    has_prefix = token.endswith("*")
    body = token[:-1] if has_prefix else token
    cleaned = re.sub(r'[^a-zA-Z0-9_/-]+', '', body)
    if not re.search(r'[a-zA-Z0-9_]', cleaned):
        return None
    if has_prefix and re.fullmatch(r'[a-zA-Z0-9_]+', cleaned or ''):
        return cleaned + "*" if cleaned else None
    return '"' + cleaned.replace('"', '""') + '"' if cleaned else None


def fts_query(query: str) -> str:
    raw_tokens = re.findall(r'"[^"]+"|[a-zA-Z0-9_/-]+\*?', query)
    tokens = [(token.upper(), token) for token in raw_tokens if token.strip()]
    operators = {"AND", "OR", "NOT"}
    has_operator = any(upper in operators for upper, _ in tokens)
    if not has_operator:
        cleaned = [term for _, token in tokens if (term := fts_term(token))]
        return " OR ".join(cleaned) or '""'

    parts: list[str] = []
    expecting_term = True
    for upper, token in tokens:
        if upper in {"AND", "OR", "NOT"}:
            if not expecting_term:
                parts.append(upper)
                expecting_term = True
            continue
        term = fts_term(token)
        if not term:
            continue
        if not expecting_term:
            parts.append("OR")
        parts.append(term)
        expecting_term = False
    while parts and parts[-1] in operators:
        parts.pop()
    return " ".join(parts) or '""'


def cmd_search(args: argparse.Namespace) -> int:
    base = root(args.path)
    db_path = base / ".akbp" / "state.db"
    if not db_path.exists():
        return cmd_query(args)
    con = sqlite3.connect(db_path)
    query_used = fts_query(args.query)
    try:
        rows = con.execute(
            "SELECT kind, object_id, path, snippet(search_index, 3, '', '', ' … ', 12), bm25(search_index) AS rank FROM search_index WHERE search_index MATCH ? ORDER BY rank LIMIT ?",
            (query_used, args.limit),
        ).fetchall()
    except sqlite3.Error:
        con.close()
        return cmd_query(args)
    finally:
        with contextlib.suppress(Exception):
            con.close()
    results = [{"type": kind, "id": object_id, "path": path, "snippet": snippet, "rank": rank} for kind, object_id, path, snippet, rank in rows]
    print(json.dumps({"query": args.query, "backend": "sqlite_fts5", "fts_query": query_used, "results": results}, indent=2, ensure_ascii=False))
    return 0



def export_manifest(base: Path, payload: dict[str, Any]) -> dict[str, Any]:
    artifact_paths = {
        "card": "akbp.json",
        "claims": "claims/claims.jsonl",
        "sources": "raw/sources/sources.jsonl",
        "entities": "graph/entities.jsonl",
        "relations": "graph/relations.jsonl",
    }
    artifact_hashes: dict[str, str | None] = {}
    for name, rel in artifact_paths.items():
        artifact_hashes[name] = file_hash(base / rel)
    counts = {
        "claims": len(payload.get("claims") or []),
        "sources": len(payload.get("sources") or []),
        "entities": len(payload.get("entities") or []),
        "relations": len(payload.get("relations") or []),
    }
    return {
        "format": "akbp-portable-bundle",
        "format_version": "0.1",
        "created_at": payload["exported_at"],
        "producer": "akbp-cli",
        "artifact_paths": artifact_paths,
        "artifact_hashes": artifact_hashes,
        "counts": counts,
        "safety": {
            "excludes_local_state": True,
            "excludes_indexes": True,
            "secret_redaction_required": True,
        },
        "verification": {
            "hash_algorithm": "sha256",
            "status": "self_describing",
        },
    }

def cmd_export(args: argparse.Namespace) -> int:
    base = root(args.path)
    payload = {
        "akbp_version": "0.1-draft",
        "exported_at": now_iso(),
        "card": json.loads((base / "akbp.json").read_text(encoding="utf-8")) if (base / "akbp.json").exists() else None,
        "claims": load_claims(base),
        "sources": load_sources(base),
        "entities": read_jsonl(base / "graph" / "entities.jsonl"),
        "relations": read_jsonl(base / "graph" / "relations.jsonl"),
    }
    payload["manifest"] = export_manifest(base, payload)
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text, end="")
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
    auto_index_if_present(base)
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


def cmd_contradict(args: argparse.Namespace) -> int:
    base = root(args.path)
    claims = load_claims(base)
    claim_ids = {c.get("id") for c in claims}
    if args.source_claim_id not in claim_ids or args.target_claim_id not in claim_ids:
        print(json.dumps({"ok": False, "error": "both claims must exist"}, indent=2), file=sys.stderr)
        return 1
    relation = {
        "id": stable_id("relation", "contradicts", args.source_claim_id, args.target_claim_id),
        "source": args.source_claim_id,
        "relation": "contradicts",
        "target": args.target_claim_id,
        "confidence": args.confidence,
        "evidence": args.evidence or [],
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    relations = load_relations(base)
    if not any(r.get("id") == relation["id"] for r in relations):
        relations.append(relation)
        write_relations(base, relations)
    for claim in claims:
        if claim.get("id") in {args.source_claim_id, args.target_claim_id} and claim.get("status") not in {"superseded", "redacted", "archived"}:
            claim["status"] = "contested"
            claim["updated_at"] = now_iso()
    write_jsonl(base / "claims" / "claims.jsonl", claims)
    add_log(base, "contradict", f"- Source claim: `{args.source_claim_id}`\n- Target claim: `{args.target_claim_id}`\n")
    audit(base, "contradict", {"source_claim_id": args.source_claim_id, "target_claim_id": args.target_claim_id, "relation_id": relation["id"]})
    auto_index_if_present(base)
    print(json.dumps(relation, indent=2, ensure_ascii=False))
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
    auto_index_if_present(base)
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

    s = sub.add_parser("index")
    s.add_argument("--incremental", action="store_true", help="only update changed index documents")
    s.set_defaults(func=cmd_index)

    s = sub.add_parser("search")
    s.add_argument("query")
    s.add_argument("--limit", type=int, default=10)
    s.set_defaults(func=cmd_search)

    s = sub.add_parser("export")
    s.add_argument("--output")
    s.set_defaults(func=cmd_export)

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

    s = sub.add_parser("contradict")
    s.add_argument("source_claim_id")
    s.add_argument("target_claim_id")
    s.add_argument("--confidence", default=0.5, type=float)
    s.add_argument("--evidence", action="append")
    s.set_defaults(func=cmd_contradict)

    s = sub.add_parser("supersede")
    s.add_argument("old_claim_id")
    s.add_argument("text")
    s.add_argument("--type", default="observation", choices=["fact", "decision", "preference", "workflow", "observation", "question", "warning"])
    s.add_argument("--scope", default="project", choices=["private", "project", "team", "public"])
    s.add_argument("--confidence", default=0.5, type=float)
    s.add_argument("--evidence", action="append")
    s.add_argument("--entity", action="append")
    s.set_defaults(func=cmd_supersede)

    s = sub.add_parser("ingest")
    s.add_argument("file")
    s.add_argument("--type", default="file", choices=["file", "url", "transcript", "message", "commit", "issue", "screenshot", "pdf", "audio", "video", "folder"])
    s.add_argument("--title")
    s.add_argument("--scope", default="project", choices=["private", "project", "team", "public"])
    s.add_argument("--claim", help="optional claim to create with the imported source as evidence")
    s.add_argument("--claim-type", default="observation", choices=["fact", "decision", "preference", "workflow", "observation", "question", "warning"])
    s.add_argument("--confidence", default=0.5, type=float)
    s.add_argument("--entity", action="append")
    s.add_argument("--dry-run", action="store_true", help="preview redacted import writes without changing the knowledge base")
    s.set_defaults(func=cmd_ingest)

    s = sub.add_parser("import-check")
    s.add_argument("file")
    s.add_argument("--fail-on-rejected", action="store_true", help="exit non-zero when any object is rejected for safety")
    s.set_defaults(func=cmd_import_check)

    s = sub.add_parser("import-apply")
    s.add_argument("file")
    s.add_argument("--dry-run", action="store_true", help="preview accepted source and claim records without writing")
    s.add_argument("--approved", action="store_true", help="apply accepted source and claim records after review")
    s.set_defaults(func=cmd_import_apply)

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
