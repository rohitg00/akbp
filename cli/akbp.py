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
import shlex
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


def find_kb_root(start: Path) -> Path | None:
    cursor = start.resolve()
    if cursor.is_file():
        cursor = cursor.parent
    for candidate in [cursor, *cursor.parents]:
        if (candidate / "akbp.json").exists():
            return candidate
    return None


def load_card(base: Path) -> dict[str, Any] | None:
    card_path = base / "akbp.json"
    if not card_path.exists():
        return None
    try:
        data = json.loads(card_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


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
- Read existing claims, sources, relations, and recent audit events before proposing new memory.
- Store durable claims in `claims/claims.jsonl`.
- Store human-readable synthesis in `wiki/`.
- Preserve evidence for claims whenever possible.
- Do not store secrets, credentials, tokens, cookies, or private keys.
- Prefer updating existing pages over creating duplicate pages.
- Use `akbp.context` or `akbp.session.start` before planning substantial follow-up work.

## Memory rules

- Durable claims should be specific enough for a future agent to act on.
- Every durable claim should cite a source id or a local evidence file when possible.
- Preview write-capable operations first; apply only after review or trusted local policy.
- Supersede or contradict stale claims instead of silently rewriting history.
- Keep private notes, raw logs, and secrets out of portable artifacts.

## Review policy

Agents may propose project memory, but durable writes require explicit approval.
If approval is unavailable, leave a preview or recommendation instead of mutating the knowledge base.

## Layout

```text
wiki/                human-readable compiled knowledge
claims/claims.jsonl  atomic durable claims
graph/               entities and relations
raw/sources/         immutable source material
.akbp/               local engine state and audit logs
```
"""


def adapter_profile_selection(kb_path: str) -> dict[str, Any]:
    return {
        "format": "akbp-adapter-profile-selection-v1",
        "purpose": "Help installers pick the least-privileged AKBP workflow profile before exposing memory tools.",
        "safe_default": "read_only",
        "decision_order": [
            "Use startup_context when the host only needs bounded cited recall before planning.",
            "Use read_only when the host can expose search, citation, source verification, and import checks but has no review UI.",
            "Use reviewed_write only when a separate review surface can show dry-run metadata and collect approval outside the model-generated tool call.",
        ],
        "profiles": [
            {
                "profile": "startup_context",
                "use_when": "The runtime only needs cited startup context and should not expose search or write tools yet.",
                "required_preflight": [
                    f"akbp --path {kb_path} doctor --profile startup-context",
                    "akbp.capabilities with requires_profiles:[\"startup_context\"]",
                    "akbp.session.start returns a bounded context envelope",
                ],
                "allowed_methods": ["akbp.capabilities", "akbp.status", "akbp.doctor", "akbp.session.start", "akbp.context"],
                "blocked_methods": ["akbp.remember", "akbp.ingest", "akbp.import_apply", "akbp.session.end"],
                "promotion_rule": "Upgrade to read_only only after doctor and capability negotiation pass.",
            },
            {
                "profile": "read_only",
                "use_when": "The host can preserve citations, warnings, structured errors, and context budgets but cannot safely review writes.",
                "required_preflight": [
                    f"akbp --path {kb_path} doctor --profile read-only",
                    "akbp.capabilities with requires_profiles:[\"read_only\"]",
                    "akbp.session.start returns cited items or the host continues without recalled memory",
                ],
                "allowed_methods": [
                    "akbp.capabilities",
                    "akbp.status",
                    "akbp.doctor",
                    "akbp.session.start",
                    "akbp.context",
                    "akbp.search",
                    "akbp.cite",
                    "akbp.source.verify",
                    "akbp.import_check",
                ],
                "blocked_methods": ["akbp.remember", "akbp.ingest", "akbp.import_apply", "akbp.session.end"],
                "promotion_rule": "Upgrade to reviewed_write only after a visible dry-run review and approval flow exists outside autonomous tool execution.",
            },
            {
                "profile": "reviewed_write",
                "use_when": "The host has a separate review surface and can replay the exact reviewed request with approved:true.",
                "required_preflight": [
                    f"akbp --path {kb_path} doctor --profile reviewed-writes",
                    "akbp.capabilities with requires_profiles:[\"reviewed_write\"] and write_apply_requires_approval",
                    "structured-output harness proves dry-run preview, approval_required rejection, approved:true apply, and recalled citations",
                ],
                "allowed_methods": [
                    "read_only methods",
                    "akbp.remember with dry_run:true before approved:true",
                    "akbp.ingest with dry_run:true before approved:true",
                    "akbp.session.end with dry_run:true before approved:true",
                    "akbp.import_apply with prior import_check",
                    "akbp.index after reviewed writes",
                ],
                "blocked_methods": [],
                "promotion_rule": "Do not auto-promote; require explicit installer or user action because this profile can mutate durable knowledge.",
            },
        ],
        "fallback": "When profile readiness, capability negotiation, citations, or review metadata are missing, keep the integration read-only and show the structured failure.",
    }

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


def source_hash_for_locator(base: Path, locator: str, source_type: str) -> str | None:
    if source_type != "file":
        return None
    source_path = Path(locator)
    candidates = [source_path] if source_path.is_absolute() else [base / source_path, source_path]
    for candidate in candidates:
        digest = file_hash(candidate.resolve())
        if digest:
            return digest
    return None


def add_source_record(base: Path, locator: str, source_type: str = "file", title: str | None = None, scope: str = "project") -> dict[str, Any]:
    safe_title = redact_text(title) if title else title
    source = {
        "id": stable_id("source", source_type, locator),
        "type": source_type,
        "locator": locator,
        "title": safe_title,
        "hash": source_hash_for_locator(base, locator, source_type),
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


def load_entities(base: Path) -> list[dict[str, Any]]:
    return read_jsonl(base / "graph" / "entities.jsonl")


def write_relations(base: Path, rows: list[dict[str, Any]]) -> None:
    write_jsonl(base / "graph" / "relations.jsonl", rows)


def known_evidence_ids(base: Path) -> set[str]:
    ids = {s.get("id") for s in load_sources(base) if s.get("id")}
    # Paths are still allowed for Level 1 compatibility, but source IDs are preferred.
    return {str(i) for i in ids}


IMPORT_CLAIM_LIST_LIMITS = {
    "evidence": (64, 512),
    "entities": (128, 256),
    "supersedes": (64, 256),
}


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
    for list_field, (max_items, max_item_length) in IMPORT_CLAIM_LIST_LIMITS.items():
        values = claim.get(list_field)
        if list_field == "evidence" and not isinstance(values, list):
            errors.append(f"claim {claim.get('id')} evidence must be a list")
            continue
        if values is None:
            continue
        if not isinstance(values, list):
            errors.append(f"claim {claim.get('id')} {list_field} must be a list of strings")
            continue
        if len(values) > max_items:
            errors.append(f"claim {claim.get('id')} {list_field} must contain at most {max_items} items")
        for index, item in enumerate(values):
            if not isinstance(item, str):
                errors.append(f"claim {claim.get('id')} {list_field} items must be strings")
                break
            if len(item) > max_item_length:
                errors.append(f"claim {claim.get('id')} {list_field}[{index}] must be at most {max_item_length} characters")
                break
    return errors

def audit(base: Path, event: str, data: dict[str, Any]) -> None:
    created_at = now_iso()
    write_events = {"remember", "ingest", "import_apply", "crystallize", "source_add", "contradict", "supersede", "init", "index"}
    operation = {
        "name": event,
        "actor": "akbp-cli",
        "mode": "write" if event in write_events else "read",
        "outcome": "ok",
        "approval_required": event in {"import_apply"},
        "redaction_checked": event in {"ingest", "import_apply"},
    }
    append_jsonl(base / ".akbp" / "audit.log.jsonl", {
        "id": stable_id("audit", event, created_at, json.dumps(data, sort_keys=True)),
        "event": event,
        "created_at": created_at,
        "operation": operation,
        "data": data,
    })


def write_if_missing(path: Path, content: str) -> None:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def cmd_init(args: argparse.Namespace) -> int:
    base = root(args.path)
    level = getattr(args, "level", "0")
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
    audit(base, "init", {"path": str(base), "level": level})
    print(f"Initialized AKBP Level {level} knowledge base at {base}")
    return 0


def cmd_discover(args: argparse.Namespace) -> int:
    start = root(args.path)
    kb_root = find_kb_root(start)
    if kb_root is None:
        print(json.dumps({
            "start_path": str(start),
            "found": False,
            "path": None,
            "card_path": None,
            "warnings": ["No akbp.json found in the start path or parent directories."],
            "next_steps": [
                "Run: akbp --path <kb> init",
                "For an existing KB, pass --path to a directory under that KB.",
            ],
        }, indent=2, ensure_ascii=False))
        return 1

    card = load_card(kb_root)
    artifacts = card.get("artifacts", {}) if isinstance(card, dict) else {}
    artifact_paths = {key: str(value) for key, value in artifacts.items() if isinstance(value, str)}
    artifact_status = {
        key: {
            "path": value,
            "exists": (kb_root / value).exists(),
        }
        for key, value in artifact_paths.items()
    }
    missing_artifacts = [key for key, status in artifact_status.items() if not status["exists"]]
    privacy = card.get("privacy", {}) if isinstance(card, dict) else {}
    default_scope = privacy.get("default_scope") if isinstance(privacy, dict) else None
    warnings: list[str] = []
    if card is None:
        warnings.append("akbp.json exists but could not be parsed as a JSON object.")
    if missing_artifacts:
        warnings.append("Some artifact paths from akbp.json are missing; run doctor before trusting this KB.")
    kb_arg = shlex.quote(str(kb_root))
    profile_selection = adapter_profile_selection(kb_arg)
    positioning = {
        "primary_role": "portable_reviewable_knowledge_artifacts",
        "not_a_hidden_memory_store": True,
        "source_of_truth": "human-readable markdown plus schema-backed JSONL artifacts",
        "use_with": [
            {
                "layer": "memory_server_or_runtime_cache",
                "role": "access layer for fast recall or host integration",
                "akbp_boundary": "export reviewed, cited, durable facts into AKBP before another runtime trusts them",
            },
            {
                "layer": "repository_instruction_files",
                "role": "startup rules and agent behavior hints",
                "akbp_boundary": "store cited project knowledge, lifecycle state, and portable evidence outside opaque prompt text",
            },
            {
                "layer": "tool_protocol_host",
                "role": "transport for calling local tools",
                "akbp_boundary": "negotiate capabilities, keep writes previewed, and require explicit approval before durable changes",
            },
            {
                "layer": "search_or_vector_index",
                "role": "rebuildable retrieval acceleration",
                "akbp_boundary": "keep markdown and JSONL artifacts as the inspectable source of truth",
            },
        ],
        "adapter_default": "read_only_until_doctor_and_capabilities_pass",
    }
    first_run_proof = {
        "goal": "prove cited, review-gated recall before enabling durable writes",
        "safe_default": "read_only",
        "recommended_harness": {
            "name": "structured_output_harness",
            "command": "./examples/structured-output-harness/run.sh",
            "purpose": "Machine-check response envelopes, capability negotiation, cited startup context, dry-run review metadata, approval_required stop signals, and approved recall before enabling reviewed writes.",
            "stop_policy": "Treat any harness failure as an adapter-contract failure and keep the integration read-only.",
        },
        "steps": [
            {
                "name": "doctor_read_only",
                "command": f"akbp --path {kb_arg} doctor --profile read-only",
                "expect": "KB files are valid enough for read-only adapter setup.",
            },
            {
                "name": "generate_client_config",
                "command": f"akbp --path {kb_arg} client-config --profile read-only",
                "expect": "Installer receives local stdio command, capability request, safety rules, and quality gates.",
            },
            {
                "name": "retrieve_startup_context",
                "command": f"akbp --path {kb_arg} context '<task>' --max-chars 4000",
                "expect": "Adapter receives bounded context with citations, warnings, and budget metadata.",
            },
            {
                "name": "preview_before_write",
                "command": "akbp.remember or akbp.session.end with dry_run:true",
                "expect": "Runtime shows review metadata and would-write paths without changing durable artifacts.",
            },
            {
                "name": "block_unapproved_write",
                "command": "repeat the write request without approved:true",
                "expect": "Tool server returns error.code approval_required.",
            },
        ],
        "enable_reviewed_writes_when": [
            "doctor --profile reviewed-writes passes",
            "the adapter shows dry-run preview fields to the user",
            "approved apply repeats the reviewed method, path, and params",
            "scratchpads, private logs, and raw transcripts stay outside AKBP unless promoted through review",
        ],
    }
    ten_minute_proof = {
        "format": "akbp-ten-minute-proof-v1",
        "purpose": "Show a new user or adapter installer the smallest proof that AKBP is local, cited, review-gated, and portable.",
        "user_value_gap": "Adjacent memory tools optimize for quick setup; AKBP must prove its trust boundary just as quickly.",
        "setup_claims": {
            "local_first": True,
            "requires_docker": False,
            "requires_cloud_account": False,
            "requires_secrets": False,
            "durable_source_of_truth": "AKBP.md plus schema-backed JSONL artifacts under the selected knowledge-base path",
            "rebuildable_runtime_state": ".akbp/ local indexes and caches",
        },
        "proof_steps": [
            {
                "name": "create_visible_artifacts",
                "command": f"akbp --path {kb_arg} init",
                "proves": "AKBP creates inspectable markdown and JSON files instead of hidden memory state.",
            },
            {
                "name": "check_readiness",
                "command": f"akbp --path {kb_arg} doctor --profile read-only",
                "proves": "A runtime can check readiness before trusting or exposing memory tools.",
            },
            {
                "name": "retrieve_cited_context",
                "command": f"akbp --path {kb_arg} context '<task>' --max-chars 4000 --require-citations",
                "proves": "Startup recall is bounded and citation-aware instead of an uncited summary.",
            },
            {
                "name": "preview_reviewed_write",
                "command": "akbp.remember, akbp.ingest, or akbp.session.end with dry_run:true",
                "proves": "Durable knowledge can be proposed without writing artifacts.",
            },
            {
                "name": "block_unapproved_apply",
                "command": "repeat the write request without approved:true",
                "proves": "The tool server returns approval_required instead of silently writing memory.",
            },
            {
                "name": "export_portable_bundle",
                "command": f"akbp --path {kb_arg} export --output bundle.json && akbp --path {kb_arg} export-check bundle.json --fail-on-issues",
                "proves": "Reviewed knowledge can be checked and carried across tools without local runtime state.",
            },
        ],
        "success_markers": [
            "doctor reports the requested profile ready",
            "context results either carry citations or the adapter continues without recalled AKBP memory",
            "write previews include review metadata and would-write paths",
            "unapproved writes fail with approval_required",
            "export-check passes without secret or manifest issues",
        ],
        "fallback": "If any proof step fails, keep the integration read-only and show the failing structured response.",
    }
    adapter_prompt_contract = {
        "format": "akbp-adapter-prompt-contract-v1",
        "purpose": "Give a runtime concrete prompt rules for preserving AKBP's cited, review-gated knowledge contract instead of relying on vague memory instructions.",
        "system_rules": [
            "Before planning from project memory, call akbp.session.start with the current task and a bounded max_chars value.",
            "Use only cited context items as recalled project knowledge; surface warnings and continue without recalled memory when context is empty or uncited.",
            "Do not treat runtime scratchpads, chat transcripts, private logs, or cache entries as durable AKBP knowledge.",
            "For durable writes, first call the write method with dry_run:true and show review_required, apply_instruction, warnings, and would_write.",
            "Apply a durable write only by repeating the exact reviewed method, path, and params with approved:true after approval outside the model-generated tool call.",
            "Branch on the response envelope's ok field and error.code; never parse prose as the success signal.",
        ],
        "required_startup_call": {
            "id": "session-start-1",
            "method": "akbp.session.start",
            "path": str(kb_root),
            "params": {
                "task": "current task goals and constraints",
                "limit": 5,
                "max_chars": 4000,
                "min_items": 1,
                "require_citations": True,
            },
        },
        "planning_gate": {
            "trusted_when": [
                "ok is true",
                "result.context.items is not empty",
                "each trusted item carries citations or source identifiers",
                "result.context.warnings has been surfaced to the user or adapter log",
            ],
            "fallback": "Proceed without recalled AKBP memory and do not invent prior decisions.",
        },
        "write_gate": {
            "preview_flags": {"dry_run": True},
            "apply_flags": {"approved": True},
            "required_preview_fields": ["review_required", "apply_instruction", "would_write", "warnings"],
            "approval_boundary": "Approval must happen outside the model-generated tool call.",
        },
        "recommended_harness": "./examples/structured-output-harness/run.sh",
    }

    print(json.dumps({
        "start_path": str(start),
        "found": True,
        "path": str(kb_root),
        "card_path": str(kb_root / "akbp.json"),
        "entrypoint_path": str(kb_root / "AKBP.md"),
        "entrypoint_exists": (kb_root / "AKBP.md").exists(),
        "card": {
            "schema_version": card.get("schema_version") if isinstance(card, dict) else None,
            "name": card.get("name") if isinstance(card, dict) else None,
            "root": card.get("root") if isinstance(card, dict) else None,
            "default_scope": default_scope,
            "secret_redaction": privacy.get("secret_redaction") if isinstance(privacy, dict) else None,
        },
        "artifacts": artifact_status,
        "missing_artifacts": missing_artifacts,
        "trust_boundary": {
            "read_path": str(kb_root),
            "default_scope": default_scope or "unknown",
            "write_rule": "Use dry-run previews first; apply only after approval or trusted local policy.",
            "adapter_rule": "Run doctor --profile before enabling a workflow profile.",
        },
        "positioning": positioning,
        "profile_selection": profile_selection,
        "first_run_proof": first_run_proof,
        "ten_minute_proof": ten_minute_proof,
        "adapter_prompt_contract": adapter_prompt_contract,
        "recommended_commands": {
            "doctor": f"akbp --path {kb_arg} doctor --profile read-only",
            "client_config": f"akbp --path {kb_arg} client-config --profile read-only",
            "session_start": f"akbp --path {kb_arg} context '<task>' --max-chars 4000",
        },
        "warnings": warnings,
    }, indent=2, ensure_ascii=False))
    return 0 if not warnings else 1


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


INACTIVE_CLAIM_STATUSES = {"superseded", "archived", "redacted"}


def is_inactive_claim(claim: dict[str, Any]) -> bool:
    return str(claim.get("status") or "").lower() in INACTIVE_CLAIM_STATUSES or bool(claim.get("superseded_by"))


def inactive_claim_matches(base: Path, query: str, limit: int) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for claim in load_claims(base):
        if not is_inactive_claim(claim):
            continue
        score = score_query(query, str(claim.get("text") or ""))
        if score:
            matches.append({
                "id": claim.get("id"),
                "status": claim.get("status"),
                "superseded_by": claim.get("superseded_by"),
                "score": score,
            })
    matches.sort(key=lambda item: item["score"], reverse=True)
    return matches[:limit]


def iter_markdown(base: Path) -> Iterable[tuple[str, str]]:
    for p in (base / "wiki").rglob("*.md"):
        yield str(p.relative_to(base)), p.read_text(encoding="utf-8", errors="ignore")


def collect_keyword_results(base: Path, query: str, limit: int) -> list[dict[str, Any]]:
    claims = read_jsonl(base / "claims" / "claims.jsonl")
    results: list[dict[str, Any]] = []
    for c in claims:
        if is_inactive_claim(c):
            continue
        score = score_query(query, c.get("text", ""))
        if score:
            results.append({
                "type": "claim",
                "score": score,
                "id": c["id"],
                "text": c["text"],
                "status": c.get("status"),
                "evidence": c.get("evidence", []),
            })
    for rel, text in iter_markdown(base):
        score = score_query(query, text)
        if score:
            snippet = re.sub(r"\s+", " ", text).strip()[:240]
            results.append({"type": "page", "score": score, "path": rel, "snippet": snippet})
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]


def collect_fts_results(base: Path, query: str, limit: int) -> list[dict[str, Any]] | None:
    db_path = base / ".akbp" / "state.db"
    if not db_path.exists():
        return None
    query_used = fts_query(query)
    if not query_used:
        return []
    claims_by_id = {str(c.get("id")): c for c in load_claims(base)}
    con = sqlite3.connect(db_path)
    try:
        rows = con.execute(
            "SELECT kind, object_id, path, snippet(search_index, 3, '', '', ' … ', 12), bm25(search_index) AS rank FROM search_index WHERE search_index MATCH ? ORDER BY rank LIMIT ?",
            (query_used, max(limit + 20, limit * 8)),
        ).fetchall()
    except sqlite3.Error:
        return None
    finally:
        con.close()
    results: list[dict[str, Any]] = []
    for kind, object_id, path, snippet, rank in rows:
        score = -float(rank)
        if kind == "claim":
            claim = claims_by_id.get(str(object_id), {})
            if is_inactive_claim(claim):
                continue
            results.append({
                "type": "claim",
                "score": score,
                "rank": rank,
                "id": object_id,
                "path": path,
                "text": claim.get("text") or snippet,
                "status": claim.get("status"),
                "snippet": snippet,
                "evidence": claim.get("evidence", []),
                "backend": "sqlite_fts5",
            })
        elif kind == "page":
            results.append({
                "type": "page",
                "score": score,
                "rank": rank,
                "id": object_id,
                "path": path,
                "snippet": snippet,
                "backend": "sqlite_fts5",
            })
        else:
            citations = [object_id] if kind == "source" else []
            results.append({
                "type": kind,
                "score": score,
                "rank": rank,
                "id": object_id,
                "path": path,
                "snippet": snippet,
                "citations": citations,
                "backend": "sqlite_fts5",
            })
    kind_priority = {"claim": 0, "source": 1, "entity": 1, "relation": 1, "page": 2}
    results.sort(key=lambda item: (kind_priority.get(str(item.get("type")), 3), item.get("rank", 0)))
    return results[:limit]


def collect_results(base: Path, query: str, limit: int) -> list[dict[str, Any]]:
    fts_results = collect_fts_results(base, query, limit)
    if fts_results is not None:
        return fts_results
    return collect_keyword_results(base, query, limit)


def source_drift_warnings(base: Path, results: list[dict[str, Any]], limit: int) -> list[str]:
    cited: set[str] = set()
    for result in results:
        if result.get("type") == "claim":
            cited.update(str(item) for item in result.get("evidence", []) if str(item).startswith("source_"))
        elif result.get("type") == "source" and result.get("id"):
            cited.add(str(result["id"]))
        for citation in result.get("citations", []):
            if str(citation).startswith("source_"):
                cited.add(str(citation))
    if not cited:
        return []

    source_check = verify_sources(base)
    by_id: dict[str, str] = {}
    for item in source_check.get("changed", []):
        by_id[str(item.get("id"))] = "changed"
    for item in source_check.get("missing", []):
        by_id[str(item.get("id"))] = "missing"

    warnings = [
        f"Cited source {source_id} is {by_id[source_id]}; run source verify before trusting dependent claims."
        for source_id in sorted(cited)
        if source_id in by_id
    ]
    return warnings[:limit]


def cmd_query(args: argparse.Namespace) -> int:
    base = root(args.path)
    results = collect_results(base, args.query, args.limit)
    inactive_matches = inactive_claim_matches(base, args.query, args.limit)
    warnings = source_drift_warnings(base, results, args.limit)
    if inactive_matches:
        skipped = ", ".join(str(item["id"]) for item in inactive_matches)
        warnings.append(f"Skipped inactive matching claims: {skipped}")
    out = {"query": args.query, "results": results, "warnings": warnings}
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


def result_to_context_item(result: dict[str, Any]) -> dict[str, Any]:
    if result["type"] == "claim":
        return {
            "id": result["id"],
            "type": "claim",
            "summary": result["text"],
            "score": result["score"],
            "backend": result.get("backend", "keyword"),
            "citations": result.get("evidence", []),
            "freshness": str(result.get("status") or "unknown"),
        }
    if result["type"] in {"source", "entity", "relation"}:
        return {
            "id": result["id"],
            "type": result["type"],
            "summary": result["snippet"],
            "score": result["score"],
            "backend": result.get("backend", "keyword"),
            "citations": result.get("citations", [result["id"]]),
            "freshness": "unknown",
        }
    return {
        "id": result["path"],
        "type": "page",
        "summary": result["snippet"],
        "score": result["score"],
        "backend": result.get("backend", "keyword"),
        "citations": [result["path"]],
        "freshness": "unknown",
    }


def apply_context_budget(pack: dict[str, Any], max_chars: int | None) -> dict[str, Any]:
    if max_chars is None:
        return pack
    remaining = max_chars
    budgeted_items: list[dict[str, Any]] = []
    clipped = 0
    omitted = 0
    original_chars = sum(len(str(item.get("summary", ""))) for item in pack["items"])
    original_items = len(pack["items"])
    for item in pack["items"]:
        summary = str(item.get("summary", ""))
        if remaining <= 0:
            omitted += 1
            continue
        if len(summary) > remaining:
            if remaining > 3:
                clipped_summary = summary[: remaining - 3].rstrip()
                clipped_summary = f"{clipped_summary}..." if clipped_summary else "..."[:remaining]
            else:
                clipped_summary = summary[:remaining]
            item = {**item, "summary": clipped_summary}
            clipped += 1
        budgeted_items.append(item)
        remaining -= len(str(item.get("summary", "")))
    pack["items"] = budgeted_items
    final_chars = sum(len(str(item.get("summary", ""))) for item in pack["items"])
    pack["budget"] = {
        "max_chars": max_chars,
        "summary_chars": final_chars,
        "original_summary_chars": original_chars,
        "truncated": bool(clipped or omitted),
        "truncated_items": clipped + omitted,
        "clipped_items": clipped,
        "omitted_items": omitted,
        "items_before_budget": original_items,
        "items_after_budget": len(budgeted_items),
    }
    if clipped or omitted:
        pack["warnings"].append(f"Context budget truncated: clipped {clipped} item(s) and omitted {omitted} item(s); increase max_chars or lower limit for more detail.")
    return pack


def context_quality(pack: dict[str, Any], min_items: int, require_citations: bool, fail_on_warnings: bool = False) -> dict[str, Any]:
    items = pack.get("items", [])
    warnings = pack.get("warnings", [])
    uncited = [
        str(item.get("id"))
        for item in items
        if not item.get("citations")
    ]
    failed: list[str] = []
    if len(items) < min_items:
        failed.append(f"minimum_items:{len(items)}<{min_items}")
    if require_citations and uncited:
        failed.append(f"uncited_items:{','.join(uncited)}")
    if fail_on_warnings and warnings:
        failed.append(f"warnings:{len(warnings)}")
    return {
        "ok": not failed,
        "minimum_items": min_items,
        "require_citations": require_citations,
        "fail_on_warnings": fail_on_warnings,
        "items": len(items),
        "uncited_items": uncited,
        "warnings": len(warnings),
        "failed": failed,
    }


def cmd_context(args: argparse.Namespace) -> int:
    base = root(args.path)
    results = collect_results(base, args.task, args.limit)
    inactive_matches = inactive_claim_matches(base, args.task, args.limit)
    warnings = [] if results else ["No matching AKBP context found."]
    warnings.extend(source_drift_warnings(base, results, args.limit))
    if inactive_matches:
        skipped = ", ".join(str(item["id"]) for item in inactive_matches)
        warnings.append(f"Skipped inactive matching claims: {skipped}")
    pack = {
        "query": args.task,
        "generated_at": now_iso(),
        "items": [result_to_context_item(r) for r in results],
        "warnings": warnings,
    }
    pack = apply_context_budget(pack, args.max_chars)
    pack["quality"] = context_quality(pack, args.min_items, args.require_citations, args.fail_on_warnings)
    if not pack["quality"]["ok"]:
        pack["warnings"].append("Context quality gate failed: " + "; ".join(pack["quality"]["failed"]))
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
    return 0 if pack["quality"]["ok"] else 1


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
        r"(?i)\b[A-Z0-9_]*(api[_-]?key|token|secret|password)\s*[:=]\s*[^\s`'\"]+",
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
    raw_title = args.title or source_path.stem.replace("-", " ").replace("_", " ").title()
    title = redact_text(raw_title)
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
                ".akbp/audit.log.jsonl",
            ],
        }, indent=2, ensure_ascii=False))
        return 0

    ensure_dirs(base)
    source = add_source_record(base, str(source_path), args.type, title, args.scope)
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



def infer_import_kind(item: dict[str, Any]) -> str:
    explicit = item.get("kind")
    if explicit:
        return str(explicit)
    if "text" in item:
        return "claim"
    if "locator" in item or str(item.get("id", "")).startswith("source_"):
        return "source"
    return str(item.get("type") or "object")


def import_jsonl_objects(source: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    raw_text = source.read_text(encoding="utf-8", errors="ignore")
    stripped = raw_text.lstrip()
    if stripped.startswith("{"):
        try:
            bundle = json.loads(raw_text)
        except json.JSONDecodeError:
            bundle = None
        if isinstance(bundle, dict) and isinstance(bundle.get("manifest"), dict) and bundle["manifest"].get("format") == "akbp-portable-bundle":
            return import_bundle_objects(bundle)

    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for line_number, line in enumerate(raw_text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append({"line": line_number, "error": exc.msg})
            continue
        item_id = str(item.get("id") or f"line-{line_number}") if isinstance(item, dict) else f"line-{line_number}"
        kind = infer_import_kind(item) if isinstance(item, dict) else "object"
        raw = json.dumps(item, sort_keys=True, ensure_ascii=False)
        safe = redact_text(raw)
        if safe != raw:
            rejected.append({"id": item_id, "kind": kind, "line": line_number, "reason": "secret_like_value_redacted"})
        else:
            accepted.append({"id": item_id, "kind": kind, "line": line_number, "object": item})
    return accepted, rejected, errors


def import_bundle_objects(bundle: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    line_number = 0
    for section, kind in [("sources", "source"), ("claims", "claim")]:
        objects = bundle.get(section, [])
        if not isinstance(objects, list):
            errors.append({"line": line_number + 1, "error": f"bundle {section} must be an array"})
            continue
        for item in objects:
            line_number += 1
            item_id = str(item.get("id") or f"{section}-{line_number}") if isinstance(item, dict) else f"{section}-{line_number}"
            if not isinstance(item, dict):
                rejected.append({"id": item_id, "kind": kind, "line": line_number, "reason": "object must be a JSON object"})
                continue
            imported = dict(item)
            imported["kind"] = kind
            raw = json.dumps(imported, sort_keys=True, ensure_ascii=False)
            safe = redact_text(raw)
            if safe != raw:
                rejected.append({"id": item_id, "kind": kind, "line": line_number, "reason": "secret_like_value_redacted"})
            else:
                accepted.append({"id": item_id, "kind": kind, "line": line_number, "object": imported})
    return accepted, rejected, errors


def public_import_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"id": item["id"], "kind": item["kind"], "line": item["line"], **({"reason": item["reason"]} if "reason" in item else {})} for item in items]


def import_review_summary(
    normalized: list[tuple[str, dict[str, Any], int]],
    rejected: list[dict[str, Any]],
    errors: list[dict[str, Any]],
) -> dict[str, Any]:
    source_ids = {str(record.get("id")) for kind, record, _line in normalized if kind == "source"}
    claims = [record for kind, record, _line in normalized if kind == "claim"]
    claims_without_evidence = [
        str(record.get("id"))
        for record in claims
        if not record.get("evidence")
    ]
    claims_without_source_evidence = [
        str(record.get("id"))
        for record in claims
        if record.get("evidence")
        and not any(isinstance(evidence, str) and evidence in source_ids for evidence in record.get("evidence") or [])
    ]
    rejected_reasons: dict[str, int] = {}
    for item in rejected:
        reason = str(item.get("reason") or "rejected")
        rejected_reasons[reason] = rejected_reasons.get(reason, 0) + 1
    ready = not errors and not rejected and not claims_without_evidence and not claims_without_source_evidence
    next_actions = []
    if errors:
        next_actions.append("Fix malformed JSON before review.")
    if rejected:
        next_actions.append("Resolve rejected records before import-apply.")
    if claims_without_evidence:
        next_actions.append("Add source evidence for every durable claim before trusting the import.")
    if claims_without_source_evidence:
        next_actions.append("Link imported claims to registered source ids before treating the import as reviewed memory.")
    if ready:
        next_actions.append("Run import-apply --dry-run, review would_write ids, then repeat with --approved.")
    return {
        "ready_for_reviewed_apply": ready,
        "source_count": len(source_ids),
        "claim_count": len(claims),
        "claims_without_evidence": claims_without_evidence,
        "claims_without_source_evidence": claims_without_source_evidence,
        "rejected_reasons": rejected_reasons,
        "next_actions": next_actions,
    }


def normalize_import_object(item: dict[str, Any]) -> tuple[str | None, dict[str, Any] | None, str | None]:
    if not isinstance(item, dict):
        return None, None, "object must be a JSON object"
    kind = infer_import_kind(item)
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
            "evidence": item.get("evidence", []),
            "entities": item.get("entities", []),
            "supersedes": item.get("supersedes", []),
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


def import_reference_rejections(base: Path, normalized: list[tuple[str, dict[str, Any], int]]) -> list[dict[str, Any]]:
    known_source_ids = {source.get("id") for source in load_sources(base) if source.get("id")}
    known_source_ids.update(record.get("id") for kind, record, _line in normalized if kind == "source")
    rejected: list[dict[str, Any]] = []
    for kind, record, line in normalized:
        if kind != "claim":
            continue
        for evidence in record.get("evidence") or []:
            if isinstance(evidence, str) and evidence.startswith("source_") and evidence not in known_source_ids:
                rejected.append({
                    "id": record.get("id", f"line-{line}"),
                    "kind": kind,
                    "line": line,
                    "reason": f"unknown evidence source id: {evidence}",
                })
                break
    return rejected


def import_duplicate_rejections(normalized: list[tuple[str, dict[str, Any], int]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    rejected: list[dict[str, Any]] = []
    for kind, record, line in normalized:
        record_id = str(record.get("id") or f"line-{line}")
        key = (kind, record_id)
        if key in seen:
            rejected.append({
                "id": record_id,
                "kind": kind,
                "line": line,
                "reason": f"duplicate import id: {record_id}",
            })
            continue
        seen.add(key)
    return rejected


def cmd_import_check(args: argparse.Namespace) -> int:
    source = Path(args.file).resolve()
    if not source.exists() or not source.is_file():
        print(json.dumps({"ok": False, "error": f"file not found: {source}"}, indent=2), file=sys.stderr)
        return 1
    accepted, rejected, errors = import_jsonl_objects(source)
    checked_count = len(accepted) + len(rejected)
    normalized: list[tuple[str, dict[str, Any], int]] = []
    accepted_by_line = {item["line"]: item for item in accepted}
    for item in accepted:
        kind, record, error = normalize_import_object(item["object"])
        if error or record is None or kind is None:
            rejected.append({"id": item["id"], "kind": kind or item["kind"], "line": item["line"], "reason": error or "invalid_import_object"})
            accepted_by_line.pop(item["line"], None)
            continue
        normalized.append((kind, record, item["line"]))
    for item in [*import_reference_rejections(root(args.path), normalized), *import_duplicate_rejections(normalized)]:
        rejected.append(item)
        accepted_by_line.pop(item["line"], None)
    accepted_public = public_import_items(list(accepted_by_line.values()))
    accepted_lines = {item["line"] for item in accepted_public}
    reviewed_normalized = [item for item in normalized if item[2] in accepted_lines]
    failed = bool(errors) or (bool(rejected) and bool(getattr(args, "fail_on_rejected", False)))
    print(json.dumps({
        "ok": not failed,
        "file": str(source),
        "checked": checked_count,
        "accepted_count": len(accepted_public),
        "rejected_count": len(rejected),
        "error_count": len(errors),
        "fail_on_rejected": bool(getattr(args, "fail_on_rejected", False)),
        "accepted": accepted_public,
        "rejected": public_import_items(rejected),
        "errors": errors,
        "review": import_review_summary(reviewed_normalized, rejected, errors),
    }, indent=2, ensure_ascii=False))
    return 1 if failed else 0




def cmd_import_apply(args: argparse.Namespace) -> int:
    base = root(args.path)
    ensure_dirs(base)
    source = Path(args.file).resolve()
    if not source.exists() or not source.is_file():
        print(json.dumps({
            "ok": False,
            "file": str(source),
            "dry_run": bool(args.dry_run),
            "applied": False,
            "checked": 0,
            "accepted_count": 0,
            "rejected_count": 0,
            "error_count": 1,
            "would_write": {
                "sources": [],
                "claims": [],
            },
            "skipped_existing": {
                "sources": [],
                "claims": [],
            },
            "accepted": [],
            "rejected": [],
            "errors": [{"line": 1, "error": f"file not found: {source}"}],
        }, indent=2, ensure_ascii=False))
        return 1
    accepted, rejected, errors = import_jsonl_objects(source)
    checked_count = len(accepted) + len(rejected)
    normalized: list[tuple[str, dict[str, Any], int]] = []
    for item in accepted:
        kind, record, error = normalize_import_object(item["object"])
        if error or record is None or kind is None:
            rejected.append({"id": item["id"], "kind": kind or item["kind"], "line": item["line"], "reason": error or "invalid_import_object"})
            continue
        normalized.append((kind, record, item["line"]))
    rejected.extend(import_reference_rejections(base, normalized))
    rejected.extend(import_duplicate_rejections(normalized))
    rejected_lines = {item["line"] for item in rejected}
    normalized = [item for item in normalized if item[2] not in rejected_lines]
    if errors or rejected:
        result = {
            "ok": False,
            "file": str(source),
            "dry_run": bool(args.dry_run),
            "applied": False,
            "checked": checked_count,
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
            "review": import_review_summary(normalized, rejected, errors),
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 1
    review = import_review_summary(normalized, [], [])
    if not review["ready_for_reviewed_apply"]:
        result = {
            "ok": False,
            "file": str(source),
            "dry_run": bool(args.dry_run),
            "applied": False,
            "checked": checked_count,
            "accepted_count": len(normalized),
            "rejected_count": 0,
            "error_count": 1,
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
            "rejected": [],
            "errors": [{"line": 1, "error": "import review is not ready for durable apply"}],
            "review": review,
            "review_required": True,
            "apply_instruction": "Fix review.next_actions, then rerun import-check and import-apply --dry-run before approved apply.",
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
        "checked": checked_count,
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
        "review": review,
    }
    if args.dry_run:
        result["review_required"] = True
        result["apply_instruction"] = "Repeat with --approved only after reviewing import-check output and dry-run would_write ids."
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
    if args.apply and args.dry_run:
        print(json.dumps({
            "ok": False,
            "error": "crystallize cannot use --apply and --dry-run together",
        }, indent=2), file=sys.stderr)
        return 1
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
        "dry_run": args.dry_run or not args.apply,
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
    card = load_card(base)
    privacy = card.get("privacy", {}) if isinstance(card, dict) else {}
    default_scope = privacy.get("default_scope") if isinstance(privacy, dict) else None
    secret_redaction = privacy.get("secret_redaction") if isinstance(privacy, dict) else None
    claims = read_jsonl(base / "claims" / "claims.jsonl")
    pages = list((base / "wiki").rglob("*.md")) if (base / "wiki").exists() else []
    sources = read_jsonl(base / "raw" / "sources" / "sources.jsonl")
    entities = load_entities(base)
    relations = load_relations(base)
    audit_events = read_jsonl(base / ".akbp" / "audit.log.jsonl")
    source_check = verify_sources(base)
    latest_claims = sorted(
        claims,
        key=lambda claim: str(claim.get("updated_at") or claim.get("created_at") or ""),
        reverse=True,
    )[: args.limit]
    status_counts: dict[str, int] = {}
    type_counts: dict[str, int] = {}
    for claim in claims:
        status = str(claim.get("status") or "unknown")
        claim_type = str(claim.get("type") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
        type_counts[claim_type] = type_counts.get(claim_type, 0) + 1
    conformance_level = "none"
    for level in ["3", "2", "1", "0"]:
        if conformance_issues(base, level)["ok"]:
            conformance_level = level
            break
    print(json.dumps({
        "path": str(base),
        "claims": len(claims),
        "sources": len(sources),
        "pages": len(pages),
        "initialized": (base / ".akbp/config.json").exists(),
        "card": (base / "akbp.json").exists(),
        "entrypoint": (base / "AKBP.md").exists(),
        "trust_boundary": {
            "default_scope": default_scope or "unknown",
            "secret_redaction": secret_redaction or "unknown",
            "write_rule": "dry_run preview before approved durable writes",
            "adapter_default": "read_only_until_doctor_and_capabilities_pass",
        },
        "counts": {
            "claims": len(claims),
            "sources": len(sources),
            "pages": len(pages),
            "entities": len(entities),
            "relations": len(relations),
            "audit_events": len(audit_events),
        },
        "claim_summary": {
            "by_status": status_counts,
            "by_type": type_counts,
            "latest": [
                {
                    "id": claim.get("id"),
                    "type": claim.get("type"),
                    "status": claim.get("status"),
                    "text": claim.get("text"),
                    "evidence": claim.get("evidence", []),
                    "updated_at": claim.get("updated_at") or claim.get("created_at"),
                }
                for claim in latest_claims
            ],
        },
        "source_health": {
            "ok": source_check["ok"],
            "counts": source_check["counts"],
            "attention": {
                "changed": source_check["changed"][: args.limit],
                "missing": source_check["missing"][: args.limit],
                "unchecked": source_check["unchecked"][: args.limit],
            },
        },
        "index": {
            "present": (base / ".akbp" / "state.db").exists(),
        },
        "conformance": {
            "highest_passing_level": conformance_level,
        },
    }, indent=2))
    return 0




def doctor_checks(base: Path) -> list[dict[str, Any]]:
    claims = load_claims(base)
    sources = load_sources(base)
    source_check = verify_sources(base)
    index_present = (base / ".akbp" / "state.db").exists()
    conformance = {level: conformance_issues(base, level) for level in ["0", "1", "2", "3"]}
    checks: list[dict[str, Any]] = [
        {
            "id": "entrypoint",
            "ok": (base / "AKBP.md").exists(),
            "severity": "error",
            "message": "AKBP.md exists",
            "next_step": "Run: akbp --path <kb> init",
        },
        {
            "id": "card",
            "ok": (base / "akbp.json").exists(),
            "severity": "error",
            "message": "akbp.json Knowledge Base Card exists",
            "next_step": "Run: akbp --path <kb> init",
        },
        {
            "id": "evidence",
            "ok": bool(sources),
            "severity": "warning",
            "message": "at least one source is registered",
            "next_step": "Run: akbp --path <kb> source add <file> --type file --title '<title>'",
        },
        {
            "id": "claims",
            "ok": bool(claims),
            "severity": "warning",
            "message": "at least one durable claim exists",
            "next_step": "Run: akbp --path <kb> ingest <file> --claim '<reviewed claim>'",
        },
        {
            "id": "source_health",
            "ok": source_check["ok"],
            "severity": "error",
            "message": "registered sources verify cleanly",
            "next_step": "Run: akbp --path <kb> source verify --fail-on-issue",
            "details": source_check["counts"],
        },
        {
            "id": "index",
            "ok": index_present,
            "severity": "warning",
            "message": "search index exists",
            "next_step": "Run: akbp --path <kb> index --incremental",
        },
        {
            "id": "conformance_level_1",
            "ok": conformance["1"]["ok"],
            "severity": "error",
            "message": "Level 1 structured claims and evidence pass",
            "next_step": "Run: akbp --path <kb> conformance --level 1",
            "details": conformance["1"]["issues"][:5],
        },
        {
            "id": "conformance_level_2",
            "ok": conformance["2"]["ok"],
            "severity": "warning",
            "message": "Level 2 retrieval and context packs pass",
            "next_step": "Run: akbp --path <kb> index && akbp --path <kb> conformance --level 2",
            "details": conformance["2"]["issues"][:5],
        },
    ]
    for check in checks:
        if check["ok"]:
            check.pop("next_step", None)
            if not check.get("details"):
                check.pop("details", None)
    return checks


def doctor_workflow(base: Path, checks: list[dict[str, Any]]) -> dict[str, Any]:
    by_id = {check["id"]: check for check in checks}
    claims = load_claims(base)
    source_ok = by_id["evidence"]["ok"] and by_id["source_health"]["ok"]
    blocking_ok = not any(not check["ok"] and check["severity"] == "error" for check in checks)
    stages: list[dict[str, Any]] = [
        {
            "id": "create_kb",
            "label": "Create a local knowledge base",
            "ok": by_id["entrypoint"]["ok"] and by_id["card"]["ok"],
            "next_step": "Run: akbp --path <kb> init",
        },
        {
            "id": "register_evidence",
            "label": "Register source material as evidence",
            "ok": source_ok,
            "next_step": by_id["source_health"].get("next_step") if by_id["evidence"]["ok"] else by_id["evidence"].get("next_step"),
        },
        {
            "id": "reviewed_claim",
            "label": "Create at least one reviewed durable claim",
            "ok": bool(claims),
            "next_step": by_id["claims"].get("next_step"),
        },
        {
            "id": "retrieval_ready",
            "label": "Build retrieval and context recall",
            "ok": by_id["index"]["ok"] and by_id["conformance_level_2"]["ok"],
            "next_step": by_id["conformance_level_2"].get("next_step") if by_id["index"]["ok"] else by_id["index"].get("next_step"),
        },
        {
            "id": "adapter_ready",
            "label": "Pass adapter-readiness checks",
            "ok": blocking_ok and all(check["ok"] for check in checks),
            "next_step": "Run: akbp --path <kb> doctor",
        },
        {
            "id": "portable_export_ready",
            "label": "Export and check a portable bundle",
            "ok": blocking_ok and bool(claims) and source_ok,
            "next_step": "Run: akbp --path <kb> export --output <bundle.json> && akbp --path <kb> export-check <bundle.json>",
        },
    ]
    for stage in stages:
        if stage["ok"]:
            stage.pop("next_step", None)
    current = next((stage["id"] for stage in stages if not stage["ok"]), None)
    return {
        "completed": sum(1 for stage in stages if stage["ok"]),
        "total": len(stages),
        "current_stage": current,
        "stages": stages,
    }


def doctor_adapter_readiness(checks: list[dict[str, Any]]) -> dict[str, Any]:
    by_id = {check["id"]: check for check in checks}
    blocking = [check for check in checks if not check["ok"] and check["severity"] == "error"]
    warnings = [check for check in checks if not check["ok"] and check["severity"] == "warning"]
    startup_context_required = ["entrypoint", "card", "source_health", "conformance_level_1"]
    read_only_required = ["entrypoint", "card", "source_health", "conformance_level_1", "index", "conformance_level_2"]
    reviewed_write_required = [check["id"] for check in checks]
    startup_context_missing = [check_id for check_id in startup_context_required if not by_id[check_id]["ok"]]
    read_only_missing = [check_id for check_id in read_only_required if not by_id[check_id]["ok"]]
    reviewed_write_missing = [check_id for check_id in reviewed_write_required if not by_id[check_id]["ok"]]
    startup_context_ready = not blocking and not startup_context_missing
    read_only_ready = not blocking and not read_only_missing
    reviewed_write_ready = not blocking and not warnings
    if reviewed_write_ready:
        recommended_profile = "reviewed_write"
    elif read_only_ready:
        recommended_profile = "read_only"
    elif startup_context_ready:
        recommended_profile = "startup_context"
    else:
        recommended_profile = "setup_only"
    return {
        "recommended_profile": recommended_profile,
        "startup_context_ready": startup_context_ready,
        "read_only_ready": read_only_ready,
        "reviewed_write_ready": reviewed_write_ready,
        "blocking_checks": [check["id"] for check in blocking],
        "startup_context_missing": startup_context_missing,
        "read_only_missing": read_only_missing,
        "reviewed_write_missing": reviewed_write_missing,
    }


def doctor_security_posture() -> dict[str, Any]:
    return {
        "write_boundary": "dry_run_preview_then_approved_apply",
        "approval_field": "approved",
        "redaction": {
            "ingest": True,
            "import_check": True,
            "import_apply": True,
            "export_check": True,
            "tool_server_error_output": True,
        },
        "adapter_rules": [
            "Start read-only unless the host can show previews and collect approval outside the model-generated tool call.",
            "Treat approval_required as a stop signal.",
            "Do not apply writes when dry-run output reports redaction, rejected imports, missing evidence, or source verification issues without human review.",
        ],
        "safe_review_methods": [
            "akbp.doctor",
            "akbp.source.verify",
            "akbp.import_check",
            "akbp.export_check",
        ],
    }


def cmd_doctor(args: argparse.Namespace) -> int:
    base = root(args.path)
    checks = doctor_checks(base)
    failing = [check for check in checks if not check["ok"]]
    blocking = [check for check in failing if check["severity"] == "error"]
    profile_key = None
    profile_ready = None
    profile_map = {
        "startup-context": "startup_context",
        "read-only": "read_only",
        "reviewed-writes": "reviewed_write",
    }
    adapter_readiness = doctor_adapter_readiness(checks)
    if args.profile:
        profile_key = profile_map[args.profile]
        profile_ready = bool(adapter_readiness[f"{profile_key}_ready"])
    print(json.dumps({
        "path": str(base),
        "ok": not blocking,
        "ready_for_adapter": not blocking and not failing,
        **({"requested_profile": profile_key, "requested_profile_ready": profile_ready} if profile_key else {}),
        "summary": {
            "passed": len(checks) - len(failing),
            "warnings": sum(1 for check in failing if check["severity"] == "warning"),
            "errors": len(blocking),
        },
        "adapter_readiness": adapter_readiness,
        "security_posture": doctor_security_posture(),
        "workflow": doctor_workflow(base, checks),
        "checks": checks,
        "next_steps": [check["next_step"] for check in failing if check.get("next_step")][: args.limit],
    }, indent=2, ensure_ascii=False))
    if blocking:
        return 1
    if profile_key and not profile_ready:
        return 1
    return 0


def cmd_client_config(args: argparse.Namespace) -> int:
    base = root(args.path)
    profile_map = {
        "startup-context": "startup_context",
        "read-only": "read_only",
        "reviewed-writes": "reviewed_write",
    }
    requested_profile = profile_map[args.profile]
    required_features = [
        "method_param_schemas",
        "capability_negotiation",
        "bounded_context",
    ]
    if requested_profile == "reviewed_write":
        required_features.append("write_apply_requires_approval")
    if args.command == "python-module":
        command = "python3"
        command_args = ["-m", "akbp_tool_server"]
    elif args.command == "repo-script":
        command = "python3"
        command_args = [str(Path(__file__).resolve().with_name("akbp_tool_server.py"))]
    else:
        command = "akbp-tool-server"
        command_args = []
    kb_path = "<AKBP_KB_PATH>" if args.portable else str(base)
    card_path = f"{kb_path}/akbp.json" if args.portable else str(base / "akbp.json")
    profile_selection = adapter_profile_selection(kb_path)
    adapter_prompt_contract = {
        "format": "akbp-adapter-prompt-contract-v1",
        "purpose": "Give the host runtime concrete prompt rules that preserve AKBP's cited, review-gated knowledge contract.",
        "profile": requested_profile,
        "system_rules": [
            "Before planning from project memory, call akbp.session.start with the current task and a bounded max_chars value.",
            "Use only cited context items as recalled project knowledge; surface warnings and continue without recalled memory when context is empty or uncited.",
            "Do not treat runtime scratchpads, chat transcripts, private logs, or cache entries as durable AKBP knowledge.",
            "For durable writes, first call the write method with dry_run:true and show review_required, apply_instruction, warnings, and would_write.",
            "Apply a durable write only by repeating the exact reviewed method, path, and params with approved:true after approval outside the model-generated tool call.",
            "Branch on the response envelope's ok field and error.code; never parse prose as the success signal.",
        ],
        "startup_request": {
            "id": "session-start-1",
            "method": "akbp.session.start",
            "path": kb_path,
            "params": {
                "task": "current task goals and constraints",
                "limit": 5,
                "max_chars": 4000,
                "min_items": 1,
                "require_citations": True,
            },
        },
        "planning_gate": {
            "required_before_planning": requested_profile in {"startup_context", "read_only", "reviewed_write"},
            "trusted_when": [
                "ok is true",
                "result.context.items is not empty",
                "each trusted item carries citations or source identifiers",
                "result.context.warnings has been surfaced to the user or adapter log",
            ],
            "fallback": "Proceed without recalled AKBP memory and do not invent prior decisions.",
        },
        "startup_trust_gate": {
            "format": "akbp-startup-trust-gate-v1",
            "purpose": "Give adapter harnesses deterministic checks before they let recalled AKBP context influence planning.",
            "required_before_planning": requested_profile in {"startup_context", "read_only", "reviewed_write"},
            "trust_conditions": {
                "response_ok": True,
                "minimum_items": 1,
                "require_citations": True,
                "require_budget": True,
                "max_chars": 4000,
                "warnings_allowed": True,
            },
            "fail_closed_on": [
                "ok is false",
                "result.context.items is empty",
                "any trusted item lacks citations or source identifiers",
                "result.context.budget.truncated is true",
                "result.context.budget.max_chars is missing or greater than the requested bound",
            ],
            "warning_action": "Surface result.context.warnings before using recalled context; if the adapter cannot surface warnings, continue without recalled AKBP memory.",
            "fallback_action": "Continue without recalled AKBP memory, do not invent prior decisions, and keep write-capable tools disabled until startup trust passes.",
            "harness": "examples/session-start-harness/run.sh",
        },
        "write_gate": {
            "required_for_apply": requested_profile == "reviewed_write",
            "preview_flags": {"dry_run": True},
            "apply_flags": {"approved": True},
            "required_preview_fields": ["review_required", "apply_instruction", "would_write", "warnings"],
            "approval_boundary": "Approval must happen outside the model-generated tool call.",
        },
        "validation": {
            "recommended_harness": "./examples/structured-output-harness/run.sh",
            "branch_on": ["ok", "error.code"],
            "preserve_fields": ["result.context.items", "result.context.warnings", "result.context.budget", "error.details"],
        },
    }
    read_only_bridge_tools = [
        {
            "tool": "akbp_capabilities",
            "method": "akbp.capabilities",
            "description": "Discover supported AKBP methods, features, profiles, and schema contracts before enabling host tools.",
            "mode": "read_only",
            "safety": {"writes": False, "requires_review_surface": False, "approval": "not_applicable"},
            "params_schema": "schemas/tool-methods.schema.json#/$defs/akbp.capabilities.params",
            "surface_fields": ["result.negotiation", "result.features", "result.profiles"],
        },
        {
            "tool": "akbp_doctor",
            "method": "akbp.doctor",
            "description": "Check knowledge-base readiness, adapter gates, and next setup steps without writing durable state.",
            "mode": "read_only",
            "safety": {"writes": False, "requires_review_surface": False, "approval": "not_applicable"},
            "params_schema": "schemas/tool-methods.schema.json#/$defs/akbp.doctor.params",
            "surface_fields": ["result.ready_for_adapter", "result.adapter_readiness", "result.next_steps"],
        },
        {
            "tool": "akbp_session_start",
            "method": "akbp.session.start",
            "description": "Retrieve bounded cited startup context for a task before the agent starts planning.",
            "mode": "read_only",
            "safety": {"writes": False, "requires_review_surface": False, "approval": "not_applicable"},
            "params_schema": "schemas/tool-methods.schema.json#/$defs/akbp.session.start.params",
            "surface_fields": ["result.session_id", "result.context.items", "result.context.warnings", "result.context.budget"],
        },
        {
            "tool": "akbp_context",
            "method": "akbp.context",
            "description": "Retrieve cited AKBP context during a session with warnings and context-budget metadata preserved.",
            "mode": "read_only",
            "safety": {"writes": False, "requires_review_surface": False, "approval": "not_applicable"},
            "params_schema": "schemas/tool-methods.schema.json#/$defs/akbp.context.params",
            "surface_fields": ["result.items", "result.warnings", "result.budget"],
        },
        {
            "tool": "akbp_search",
            "method": "akbp.search",
            "description": "Search reviewed local AKBP artifacts and return structured results without enabling writes.",
            "mode": "read_only",
            "safety": {"writes": False, "requires_review_surface": False, "approval": "not_applicable"},
            "params_schema": "schemas/tool-methods.schema.json#/$defs/akbp.search.params",
            "surface_fields": ["result.results", "result.warnings", "result.backend"],
        },
        {
            "tool": "akbp_cite",
            "method": "akbp.cite",
            "description": "Inspect a claim and its evidence before relying on recalled knowledge.",
            "mode": "read_only",
            "safety": {"writes": False, "requires_review_surface": False, "approval": "not_applicable"},
            "params_schema": "schemas/tool-methods.schema.json#/$defs/akbp.cite.params",
            "surface_fields": ["result.claim_id", "result.claim", "result.evidence"],
        },
        {
            "tool": "akbp_source_verify",
            "method": "akbp.source.verify",
            "description": "Verify cited sources and report drift or missing evidence as a maintenance gate.",
            "mode": "read_only",
            "safety": {"writes": False, "requires_review_surface": False, "approval": "not_applicable"},
            "params_schema": "schemas/tool-methods.schema.json#/$defs/akbp.source.verify.params",
            "surface_fields": ["result.ok", "result.counts", "result.issues"],
        },
        {
            "tool": "akbp_import_check",
            "method": "akbp.import_check",
            "description": "Validate an import bundle and report accepted or rejected records without applying them.",
            "mode": "read_only",
            "safety": {"writes": False, "requires_review_surface": False, "approval": "not_applicable"},
            "params_schema": "schemas/tool-methods.schema.json#/$defs/akbp.import_check.params",
            "surface_fields": ["result.ok", "result.accepted_count", "result.rejected_count", "result.errors"],
        },
    ]
    host_tool_manifest = {
        "format": "akbp-tool-host-manifest-v1",
        "purpose": "Generate host-facing read-only tools from AKBP JSONL methods without creating a second memory format.",
        "transport": "stdio-jsonl",
        "server": {
            "command": command,
            "args": command_args,
            "env": {},
        },
        "knowledge_base_path": kb_path,
        "default_mode": "read_only",
        "approval_boundary": "write tools require a separate reviewed-write surface outside the model-generated tool call",
        "tools": [
            {
                "name": entry["tool"],
                "forwards_to": entry["method"],
                "description": entry["description"],
                "mode": entry["mode"],
                "safety": entry["safety"],
                "input_schema": entry["params_schema"],
                "preserve_response_fields": entry["surface_fields"],
            }
            for entry in read_only_bridge_tools
        ],
        "preflight_requests": [
            {
                "id": "capabilities-1",
                "method": "akbp.capabilities",
                "path": kb_path,
                "params": {
                    "client": args.name,
                    "requires": required_features,
                    "requires_profiles": [requested_profile],
                },
                "expect": {
                    "ok": True,
                    "result.negotiation.satisfied": True,
                    "result.features.method_param_schemas": True,
                },
            },
            {
                "id": "doctor-1",
                "method": "akbp.doctor",
                "path": kb_path,
                "params": {"profile": requested_profile},
                "expect": {
                    "ok": True,
                    "result.requested_profile": requested_profile,
                    "result.requested_profile_ready": True,
                    f"result.adapter_readiness.{requested_profile}_ready": True,
                },
            },
            {
                "id": "session-start-1",
                "method": "akbp.session.start",
                "path": kb_path,
                "params": {
                    "task": "current task goals and constraints",
                    "limit": 5,
                    "max_chars": 4000,
                    "min_items": 1,
                    "require_citations": True,
                },
                "expect": {
                    "ok": True,
                    "result.context.items": "array",
                    "result.context.warnings": "array",
                    "result.context.budget.max_chars": 4000,
                    "result.quality.minimum_items": 1,
                    "result.quality.require_citations": True,
                },
            },
        ],
    }
    client_tool_manifest = {
        "format": "akbp-client-tool-manifest-v1",
        "purpose": "Generate host-compatible read-only tools from AKBP JSONL methods while preserving citations, structured errors, and the reviewed-write boundary.",
        "server": {
            "name": args.name,
            "command": command,
            "args": command_args,
            "env": {},
        },
        "knowledge_base_path": kb_path,
        "default_mode": "read_only",
        "transport_adapter": "stdio-jsonl-to-host-tools",
        "response_contract": {
            "preserve_envelope": True,
            "branch_on": "error.code",
            "surface_warnings": True,
            "surface_citations": True,
        },
        "tools": [
            {
                "name": entry["tool"],
                "description": entry["description"],
                "akbp_method": entry["method"],
                "mode": entry["mode"],
                "safety": entry["safety"],
                "input_schema_ref": entry["params_schema"],
                "preserve_response_fields": entry["surface_fields"],
            }
            for entry in read_only_bridge_tools
        ],
        "blocked_write_methods": [
            "akbp.remember",
            "akbp.source.add",
            "akbp.ingest",
            "akbp.import_apply",
            "akbp.index",
            "akbp.session.end",
            "akbp.crystallize_session",
            "akbp.supersede",
            "akbp.contradict",
        ],
        "approval_boundary": "Do not expose write methods as host tools until the host can render dry-run previews and collect approval outside the model-generated tool call.",
        "preflight_requests": host_tool_manifest["preflight_requests"],
    }
    host_capability_descriptor = {
        "format": "akbp-host-capability-descriptor-v1",
        "purpose": "Let tool hosts classify AKBP as a durable, cited knowledge capability before mapping methods into host-native tools.",
        "capability_type": "durable_agent_knowledge",
        "transport": "stdio-jsonl",
        "default_profile": requested_profile,
        "safe_default_profile": "read_only",
        "profile_contracts": {
            "startup_context": {
                "mode": "read_only",
                "requires_review_surface": False,
                "write_policy": "no_writes",
                "methods": ["akbp.capabilities", "akbp.status", "akbp.session.start", "akbp.context", "akbp.search"],
            },
            "read_only": {
                "mode": "read_only",
                "requires_review_surface": False,
                "write_policy": "no_writes",
                "methods": [entry["method"] for entry in read_only_bridge_tools],
            },
            "reviewed_write": {
                "mode": "reviewed_write",
                "requires_review_surface": True,
                "write_policy": "dry_run_preview_then_approved_apply",
                "preview_methods": ["akbp.remember", "akbp.ingest", "akbp.source.add", "akbp.session.end"],
                "apply_requires": {"approved": True, "same_method_path_and_params": True},
            },
        },
        "host_integration_rules": [
            "Run akbp.capabilities with requires_profiles before enabling profile-specific flows.",
            "Keep host-generated tools read-only unless the host has a visible review surface outside the model tool call.",
            "Preserve AKBP response envelopes so callers can branch on ok and error.code.",
            "Surface citations, source warnings, and context budget warnings before using recalled context for planning.",
        ],
        "read_only_methods": [entry["method"] for entry in read_only_bridge_tools],
        "blocked_until_review_surface": client_tool_manifest["blocked_write_methods"],
        "schema_refs": {
            "request": "schemas/tool-request.schema.json",
            "response": "schemas/tool-response.schema.json",
            "methods": "schemas/tool-methods.schema.json",
        },
    }
    tool_protocol_bridge_snippets = {
        "format": "akbp-tool-protocol-bridge-snippets-v1",
        "purpose": "Give tool-protocol-capable hosts copyable bridge inputs without claiming the reference JSONL server is itself a host-native tool server.",
        "direct_host_native_server": False,
        "bridge_required": True,
        "bridge_rule": "A host bridge must translate host tool calls to AKBP JSONL requests and preserve ok, result, error.code, citations, warnings, and budget fields.",
        "safe_default_profile": "read_only",
        "requested_profile": requested_profile,
        "server_process": {
            "transport": "stdio-jsonl",
            "command": command,
            "args": command_args,
            "env": {
                "AKBP_KB_PATH": kb_path,
            },
        },
        "host_server_template": {
            "toolServers": {
                "akbp": {
                    "command": "<AKBP_TOOL_BRIDGE_COMMAND>",
                    "args": [
                        "--stdio-jsonl-command",
                        command,
                        "--knowledge-base",
                        kb_path,
                        "--profile",
                        requested_profile,
                    ],
                    "env": {
                        "AKBP_KB_PATH": kb_path,
                    },
                },
            },
        },
        "required_bridge_behavior": [
            "run preflight_requests before exposing tools",
            "publish only read-only tools until doctor and capability negotiation pass",
            "map host tool input to the advertised AKBP method params schema",
            "return AKBP structured errors without converting them to prose-only failures",
            "keep durable write apply disabled unless a separate reviewed-write surface exists",
        ],
        "preflight_requests": host_tool_manifest["preflight_requests"],
        "tool_manifest_ref": "tool_protocol_bridge.host_tool_manifest",
        "fallback": "If no bridge is available, use the stdio JSONL adapter path directly and keep the integration read-only.",
    }

    config = {
        "name": args.name,
        "transport": "stdio-jsonl",
        "server": {
            "command": command,
            "args": command_args,
            "env": {},
        },
        "knowledge_base": {
            "path": kb_path,
            "card": card_path,
            "portable_template": bool(args.portable),
        },
        "knowledge_capability": {
            "type": "durable_agent_knowledge",
            "role": "portable cited knowledge substrate, not an opaque memory store",
            "source_of_truth": "AKBP markdown and JSONL artifacts under knowledge_base.path",
            "guarantees": [
                "local_first_artifacts",
                "source_backed_claims",
                "bounded_cited_retrieval",
                "dry_run_write_previews",
                "explicit_approved_apply",
                "audit_and_lifecycle_records",
                "exportable_bundle_checks",
            ],
            "default_mode": "read_only",
            "write_mode": "reviewed_write_only",
            "session_boundary": {
                "runtime_transient_state": [
                    "scratchpads",
                    "raw transcripts",
                    "private logs",
                    "per-client caches",
                ],
                "promotion_method": "akbp.session.end",
                "promotion_gate": "dry_run preview before reviewed approved:true apply",
                "trusted_durable_state": "approved AKBP artifacts with citations, lifecycle status, and audit records",
            },
            "host_mapping": {
                "read": "Expose startup, context, search, cite, source verification, and import checks first.",
                "write": "Expose preview tools only when the host can render review metadata outside the model-generated tool call.",
                "apply": "Repeat the exact reviewed method, path, and params with approved:true after explicit approval.",
                "maintenance": "Run source verification, doctor, export checks, and index refreshes as adapter health gates.",
            },
            "not_a": [
                "chat transcript dump",
                "runtime scratchpad",
                "uncited vector cache",
                "bridge-owned memory format",
                "automatic background write sink",
            ],
        },
        "host_capability_descriptor": host_capability_descriptor,
        "tool_protocol_bridge_snippets": tool_protocol_bridge_snippets,
        "profile_selection": profile_selection,
        "runtime_requirements": {
            "local_first": True,
            "network_required": False,
            "cloud_account_required": False,
            "secrets_required": [],
            "install_surface": {
                "runtime": "python3",
                "external_services_required": [],
                "docker_required": False,
                "database_required": "none; the SQLite FTS index under .akbp/ is rebuildable runtime state",
                "network_required_after_install": False,
                "first_command": "akbp discover",
                "adapter_setup_order": [
                    "resolve explicit knowledge_base.path",
                    "run akbp discover",
                    "run akbp doctor --profile read-only",
                    "generate akbp client-config --profile read-only",
                    "run generated preflight_requests before exposing tools",
                ],
            },
            "durable_state_owner": "AKBP artifacts under knowledge_base.path",
            "runtime_state_policy": "Adapters may keep ephemeral state locally, but durable memory must stay in AKBP artifacts.",
            "path_resolution": "Resolve <AKBP_KB_PATH> during install or first run when portable_template is true.",
            "tool_protocol_hosts": "Use the read-only bridge allowlist until doctor, capabilities, and startup context checks pass.",
        },
        "hosted_agent_policy": {
            "format": "akbp-hosted-agent-policy-v1",
            "purpose": "Make the boundary explicit for hosted coding agents and managed tool hosts that may not run the local stdio server beside AKBP artifacts.",
            "default_profile": "read_only",
            "safe_when": [
                "the host can reach a user-controlled bridge that preserves AKBP response envelopes",
                "the bridge exposes only the generated read-only allowlist",
                "startup preflight requests pass before recalled context affects planning",
                "durable writes are reviewed and applied from a local checkout or CI job with a visible approval step",
            ],
            "unsafe_to_enable_writes_when": [
                "the hosted agent cannot show dry-run review metadata to a human reviewer",
                "tool execution is treated as approval",
                "the bridge stores durable memory outside AKBP artifacts",
                "the host cannot preserve citations, warnings, budget fields, ok, and error.code",
            ],
            "hosted_tool_allowlist": [
                "akbp.capabilities",
                "akbp.status",
                "akbp.doctor",
                "akbp.session.start",
                "akbp.context",
                "akbp.search",
                "akbp.cite",
                "akbp.source.verify",
                "akbp.import_check",
            ],
            "blocked_apply_methods": [
                "akbp.remember",
                "akbp.ingest",
                "akbp.import_apply",
                "akbp.session.end",
                "akbp.index",
                "akbp.source.add",
                "akbp.supersede",
                "akbp.contradict",
            ],
            "write_path": "Run dry-run previews and approved applies from a local checkout or CI step that can show review_required, apply_instruction, warnings, and would_write before approved:true.",
            "fallback": "If the hosted environment cannot preserve the AKBP trust contract, expose only read-only startup context or skip AKBP memory for that run.",
        },
        "host_install_profiles": [
            {
                "host_type": "terminal_agent",
                "use_when": "A CLI coding agent can launch a local stdio process and read JSON config.",
                "safe_default_profile": "read_only",
                "setup_commands": [
                    f"akbp --path {kb_path} discover",
                    f"akbp --path {kb_path} doctor --profile read-only",
                    f"akbp --path {kb_path} client-config --profile read-only --name {args.name}",
                ],
                "first_tool": "akbp_session_start",
                "enable_writes_after": "host renders dry-run review metadata and repeats the exact reviewed request with approved:true",
            },
            {
                "host_type": "editor_agent",
                "use_when": "An IDE or editor extension needs host-native tools backed by AKBP JSONL methods.",
                "safe_default_profile": "read_only",
                "setup_commands": [
                    "generate tool_protocol_bridge.host_tool_manifest",
                    "create read-only host tools from manifest.tools",
                    "run manifest.preflight_requests before exposing tools",
                ],
                "first_tool": "akbp_session_start",
                "enable_writes_after": "separate review UI exists outside the model-generated tool call",
            },
            {
                "host_type": "managed_tool_protocol_host",
                "use_when": "A hosted or managed tool runtime can expose AKBP-backed tools but may not have a local human review surface.",
                "safe_default_profile": "read_only",
                "setup_commands": [
                    "mount or resolve an explicit AKBP knowledge_base.path before startup",
                    "publish only the read-only tools from tool_protocol_bridge.host_tool_manifest",
                    "run akbp.capabilities, akbp.doctor, and bounded akbp.session.start as preflight checks",
                    "keep durable writes disabled unless the host provides a separate approval UI",
                ],
                "first_tool": "akbp_session_start",
                "enable_writes_after": "managed host proves dry-run preview, separate human approval, and exact approved:true replay outside autonomous tool execution",
            },
            {
                "host_type": "existing_memory_server",
                "use_when": "A runtime already has a memory server, cache, or graph store and wants AKBP-compatible durable artifacts.",
                "safe_default_profile": "read_only",
                "setup_commands": [
                    "keep existing runtime memory as ephemeral cache",
                    "route durable reviewed records through akbp.remember dry_run first",
                    "preserve citations, source ids, and error.code in bridge responses",
                ],
                "first_tool": "akbp_context",
                "enable_writes_after": "migration or promotion flow passes import-check or dry-run preview without secret or citation warnings",
            },
        ],
        "managed_tool_host_bridge": {
            "format": "akbp-managed-tool-host-bridge-v1",
            "purpose": "Let tool-protocol-compatible hosts launch AKBP as a local stdio knowledge tool while preserving AKBP's cited, review-gated memory boundary.",
            "server_config": {
                "command": command,
                "args": command_args,
                "env": {},
                "transport": "stdio",
                "knowledge_base_path": kb_path,
            },
            "safe_default_profile": "read_only",
            "startup_profile": requested_profile,
            "tool_exposure": {
                "read_only_tools": [entry["tool"] for entry in read_only_bridge_tools],
                "forwards_to": {entry["tool"]: entry["method"] for entry in read_only_bridge_tools},
                "blocked_write_methods": client_tool_manifest["blocked_write_methods"],
                "enable_write_tools_only_when": [
                    "akbp.capabilities negotiation passes for reviewed_write",
                    "akbp.doctor reports adapter_readiness.reviewed_write_ready",
                    "the host shows dry-run review metadata outside model tool execution",
                    "approved apply repeats the exact reviewed method, path, and params with approved:true",
                ],
            },
            "preflight_requests": host_tool_manifest["preflight_requests"],
            "response_requirements": {
                "preserve_envelope": True,
                "branch_on": "ok and error.code",
                "surface": ["citations", "source ids", "warnings", "budget", "review_required", "would_write"],
                "do_not_store": ["raw transcripts", "scratchpads", "private chat logs", "secrets", "uncited summaries"],
            },
            "fallback": "If the host cannot preserve citations, warnings, structured errors, and dry-run review metadata, expose AKBP as read-only startup context only.",
        },
        "memory_server_bridge": {
            "purpose": "Classify AKBP beside local memory servers, tool-protocol bridges, and runtime caches without letting the bridge become the source of truth.",
            "safe_default": "read_only_substrate",
            "durable_state_owner": "AKBP markdown and JSONL artifacts under knowledge_base.path",
            "bridge_role": "transport_and_policy_glue_only",
            "promotion_contract": {
                "purpose": "Let an existing memory server promote only reviewed durable knowledge into AKBP instead of bulk-copying opaque runtime memory.",
                "candidate_records": [
                    "durable project decisions",
                    "source-backed facts",
                    "workflow constraints",
                    "supersession or contradiction records",
                ],
                "reject_records": [
                    "runtime scratchpad notes",
                    "uncited summaries",
                    "private chat logs",
                    "secret-like values",
                    "bridge-only embeddings or cache metadata",
                ],
                "required_review_fields": [
                    "record text",
                    "record type",
                    "source id or citation",
                    "lifecycle status",
                    "dry-run warnings",
                    "would-write artifact paths",
                ],
                "preflight_requests": [
                    "akbp.capabilities with read_only or reviewed_write profile requirements",
                    "akbp.doctor for adapter readiness",
                    "akbp.import_check or dry_run akbp.remember before applying promoted records",
                ],
                "apply_rule": "Apply only the exact reviewed record with approved:true after the host shows the dry-run preview outside the model tool call.",
                "fallback": "Keep the bridge read-only when citations, review metadata, or explicit approval are missing.",
            },
            "integration_modes": [
                {
                    "mode": "runtime_cache_plus_akbp",
                    "use_when": "The host already keeps ephemeral task memory or embeddings for speed.",
                    "akbp_boundary": "Only reviewed durable facts, decisions, sources, and lifecycle records are promoted into AKBP.",
                    "required_gate": "dry_run preview before any durable write",
                },
                {
                    "mode": "tool_protocol_bridge",
                    "use_when": "The host wants native tools but AKBP remains the file-backed knowledge base.",
                    "akbp_boundary": "Generate read-only host tools from tool_protocol_bridge.host_tool_manifest before exposing write previews.",
                    "required_gate": "capabilities and doctor preflight must pass",
                },
                {
                    "mode": "migration_review",
                    "use_when": "Existing memories, notes, or exports need cleanup before reuse.",
                    "akbp_boundary": "Run import-check and dry-run import-apply, then approve only cited and non-secret records.",
                    "required_gate": "import-check accepted records and surfaced rejections",
                },
            ],
            "must_preserve": [
                "AKBP response envelope with ok, result, and error.code",
                "citations, source ids, source drift warnings, and context budget",
                "dry-run review metadata before approved writes",
                "export-checkable artifacts independent of bridge-local metadata",
            ],
            "disable_or_warn_when": [
                "the bridge stores durable memory in its own opaque format",
                "recalled context has no citations or source ids",
                "write tools can apply without dry_run preview and explicit approved:true",
                "export or import checks depend on bridge-local state",
            ],
        },
        "memory_landscape_fit": {
            "format": "akbp-memory-landscape-fit-v1",
            "purpose": "Help adapter installers explain where AKBP fits beside fast tool-protocol memory servers, local SQLite memories, graph memories, context reducers, and product-native agent memory.",
            "observed_user_pull": [
                "one-command local setup for coding-agent memory",
                "shared memory across tool-protocol-compatible tools",
                "knowledge graph or hierarchical recall over long-running projects",
                "lower context-window pressure at session start",
                "persistent project facts that survive across agent runs",
            ],
            "akbp_should_own": [
                "reviewed durable project knowledge",
                "cited startup context",
                "source-backed lifecycle and supersession records",
                "export-checkable markdown and JSONL artifacts",
                "adapter contracts that fail closed when citations, schemas, or approval are missing",
            ],
            "akbp_should_not_own": [
                "opaque chat-memory databases",
                "raw transcript ingestion without review",
                "bridge-owned embeddings as durable truth",
                "automatic background writes from autonomous tool calls",
                "uncited summaries promoted as project facts",
            ],
            "installer_positioning": "Present AKBP as the portable trust layer beside memory tools: use other stores for speed or runtime UX, then promote only cited, reviewed durable records into AKBP.",
            "comparison_checks": [
                "Can the user inspect and version the durable artifacts without the adapter?",
                "Does recalled context carry citations or source ids?",
                "Can writes be previewed with dry_run:true before approved:true apply?",
                "Can stale knowledge be superseded or contradicted without deleting history?",
                "Can export-check and import-check run without bridge-local state?",
            ],
            "fallback": "If an adjacent memory tool cannot preserve citations, review metadata, or exportable artifacts, keep AKBP read-only and treat that tool as an ephemeral hint source.",
        },
        "native_memory_interop": {
            "format": "akbp-native-memory-interop-v1",
            "purpose": "Prevent dual-memory drift when a coding agent, tool memory server, or hosted assistant already has product-native memory.",
            "safe_default": "akbp_as_cited_source_of_truth",
            "read_order": [
                "retrieve cited AKBP startup context before planning from product-native memory",
                "use product-native or external tool memory only as ephemeral hints until AKBP citations confirm durable project facts",
                "surface conflicts between native memory and AKBP claims before acting on either source",
            ],
            "write_order": [
                "keep native memory writes disabled or ephemeral for project decisions during first-run setup",
                "promote durable project facts through akbp.remember or akbp.ingest with dry_run:true",
                "apply only after the exact preview is approved with approved:true",
                "refresh AKBP index before expecting later sessions to recall the promoted record",
            ],
            "conflict_policy": {
                "prefer": "active AKBP claims with citations and verified sources",
                "when_native_memory_disagrees": "treat native memory as unreviewed evidence, then add a source and supersede or contradict the AKBP claim after review",
                "when_akbp_is_empty": "continue without recalled durable memory and do not bulk-import uncited native memories",
            },
            "reject_promotion_when": [
                "the native memory item has no source or citation",
                "the item is runtime scratch, a private chat fragment, a secret-like value, or bridge-only cache metadata",
                "the host cannot show dry-run review metadata and approval outside model tool execution",
            ],
            "adapter_action": "Expose this policy in installer UI or agent instructions whenever the host advertises built-in memory, external memory tools, or an external memory server.",
            "fallback": "Keep AKBP read-only and leave native memory unpromoted when citations, review metadata, or explicit approval are missing.",
        },
        "multi_client_scope": {
            "purpose": "Let several coding-agent, editor, or local-assistant clients share one reviewed knowledge base without creating hidden per-client memory stores.",
            "shared_kb_path": kb_path,
            "client_identity_field": "startup.params.client",
            "default_mode": "read_only",
            "scope_rule": "All clients read from the same selected knowledge_base.path; durable writes use dry-run previews and approved applies against that same path.",
            "isolation_rule": "Runtime scratchpads, private chat logs, and per-client caches stay outside AKBP until promoted through a reviewed write.",
            "conflict_policy": "Use lifecycle methods such as supersede or contradict for stale claims; never overwrite or delete another client's reviewed claim silently.",
            "audit_policy": "Durable writes append audit records so maintainers can see which approved operation changed shared knowledge.",
            "safe_for_public_templates": bool(args.portable),
        },
        "scope_selection": {
            "purpose": "Make the first-run trust question explicit before an adapter creates or reuses durable memory.",
            "selected_scope": "repo_local",
            "selected_kb_path": kb_path,
            "safe_default": "repo_local_read_only",
            "installer_prompt": "Which reviewed AKBP knowledge base should this runtime trust for durable project memory?",
            "scope_options": [
                {
                    "scope": "repo_local",
                    "recommended": True,
                    "use_when": "The agent is working in one repository and needs project decisions, constraints, incidents, or architecture context.",
                    "trust_boundary": "Only reviewed project knowledge with citations belongs in this KB.",
                    "avoid": "Do not mix personal assistant memory, private chat exports, or unrelated project notes into the repo-local KB.",
                    "default_profile": "read_only",
                },
                {
                    "scope": "team_shared",
                    "recommended": False,
                    "use_when": "Multiple engineers or agents need the same reviewed project knowledge.",
                    "trust_boundary": "Treat imported or approved records as team-visible project knowledge.",
                    "avoid": "Do not promote one person's unreviewed local notes as shared truth.",
                    "default_profile": "read_only",
                },
                {
                    "scope": "personal_assistant",
                    "recommended": False,
                    "use_when": "A local assistant needs private user preferences or workflow context across projects.",
                    "trust_boundary": "Keep this KB outside public repos and start read-only.",
                    "avoid": "Do not commit personal preferences, DMs, credentials, or private logs to a public repository.",
                    "default_profile": "read_only",
                },
                {
                    "scope": "migration",
                    "recommended": False,
                    "use_when": "Existing memory exports, notes, or JSONL records need review before reuse.",
                    "trust_boundary": "Run import-check and dry-run import-apply before approving durable records.",
                    "avoid": "Do not bulk-load stale, uncited, or secret-bearing memory just because it exists.",
                    "default_profile": "read_only",
                },
            ],
            "adapter_rules": [
                "Resolve scope_selection.selected_kb_path before capability negotiation.",
                "Start with scope_selection.safe_default unless the installer has an explicit reviewed-write surface.",
                "Keep per-client caches and chat transcripts outside AKBP until promoted through dry-run review and approval.",
                "Show the selected scope and trust boundary in setup UI before enabling recalled context.",
            ],
        },
        "ten_minute_proof": {
            "format": "akbp-ten-minute-proof-v1",
            "purpose": "Let installer UIs prove AKBP's user value before positioning it as another memory store.",
            "user_value_gap": "Fast local memory tools make setup friction visible; AKBP must prove local, cited, review-gated, portable memory in the first run.",
            "setup_claims": {
                "local_first": True,
                "requires_docker": False,
                "requires_cloud_account": False,
                "requires_secrets": False,
                "durable_source_of_truth": "AKBP markdown and JSONL artifacts under knowledge_base.path",
                "rebuildable_runtime_state": ".akbp/ local indexes and caches",
            },
            "proof_steps": [
                {
                    "name": "resolve_visible_kb",
                    "run": "knowledge_base",
                    "proves": "The adapter knows the explicit AKBP path before trusting recalled memory.",
                },
                {
                    "name": "check_readiness",
                    "run": "health_check",
                    "proves": "The requested workflow profile is checked before host tools are exposed.",
                },
                {
                    "name": "retrieve_cited_context",
                    "run": "session_start",
                    "proves": "Startup context is bounded and citation-aware.",
                },
                {
                    "name": "preview_reviewed_write",
                    "run": "write method with dry_run:true",
                    "proves": "Durable writes can be reviewed without changing AKBP artifacts.",
                },
                {
                    "name": "block_unapproved_apply",
                    "run": "same write method without approved:true",
                    "proves": "The server returns approval_required instead of silently writing memory.",
                },
                {
                    "name": "export_checked_bundle",
                    "run": "akbp export followed by akbp export-check --fail-on-issues",
                    "proves": "Reviewed knowledge is portable without bridge-owned or index-only state.",
                },
            ],
            "success_markers": [
                "health_check reports requested_profile_ready",
                "session_start returns cited items or the host continues without recalled memory",
                "dry-run preview returns review metadata and would-write paths",
                "unapproved writes fail with approval_required",
                "export-check passes before sharing or importing knowledge",
            ],
            "fallback": "Keep the integration read-only when any proof step fails.",
        },
        "first_run_sequence": {
            "purpose": "Give adapter installers an ordered setup path before any runtime trusts or writes memory.",
            "stop_policy": "Stop at the first failed required step, show the structured failure, and keep the integration read-only.",
            "steps": [
                {
                    "step": "resolve_knowledge_base",
                    "run": "knowledge_base",
                    "required": True,
                    "expect": {
                        "knowledge_base.path": kb_path,
                        "knowledge_base.card": card_path,
                    },
                    "on_failure": "Run akbp init or replace <AKBP_KB_PATH> before starting the adapter.",
                },
                {
                    "step": "negotiate_capabilities",
                    "run": "startup",
                    "required": True,
                    "request_id": "capabilities-1",
                    "expect": {
                        "ok": True,
                        "result.negotiation.satisfied": True,
                        "result.features.method_param_schemas": True,
                    },
                    "on_failure": "Disable unsupported methods or profiles and refresh the generated client-config.",
                },
                {
                    "step": "check_adapter_readiness",
                    "run": "health_check",
                    "required": True,
                    "request_id": "doctor-1",
                    "expect": {
                        "ok": True,
                        "result.requested_profile": requested_profile,
                        "result.requested_profile_ready": True,
                        f"result.adapter_readiness.{requested_profile}_ready": True,
                    },
                    "on_failure": "Show result.next_steps and use the recommended lower-risk profile until the knowledge base is ready.",
                },
                {
                    "step": "retrieve_cited_startup_context",
                    "run": "session_start",
                    "required": requested_profile in {"startup_context", "read_only", "reviewed_write"},
                    "request_id": "session-start-1",
                    "expect": {
                        "ok": True,
                        "result.context.items": "array",
                        "result.context.budget.max_chars": 4000,
                    },
                    "on_failure": "Continue without recalled memory, surface the warning, and do not invent prior project decisions.",
                },
                {
                    "step": "enable_writes_only_after_review_surface",
                    "run": "reviewed_writes",
                    "required": requested_profile == "reviewed_write",
                    "expect": {
                        "dry_run_preview_visible": True,
                        "approval_outside_model_tool_call": True,
                        "approved_apply_repeats_exact_request": True,
                    },
                    "on_failure": "Keep write-capable tools disabled and use the read-only allowlist.",
                },
            ],
        },
        "adapter_contract_harness": {
            "recommended": True,
            "command": "./examples/structured-output-harness/run.sh",
            "run_after": ["session-start-harness", "generated preflight_requests"],
            "proves": [
                "stable response envelope with id, ok, result, and error",
                "capability negotiation disables unsupported features and profiles",
                "doctor exposes adapter readiness and reviewed-write posture",
                "startup context returns cited items before planning from memory",
                "dry-run write previews expose review_required, apply_instruction, and would_write",
                "unapproved writes stop with error.code approval_required",
                "approved apply plus index refresh returns cited recall for the reviewed claim",
            ],
            "stop_policy": "Fail closed: keep write-capable host tools disabled and continue read-only until the harness passes.",
        },
        "adapter_prompt_contract": adapter_prompt_contract,
        "startup": {
            "id": "capabilities-1",
            "method": "akbp.capabilities",
            "path": kb_path,
            "params": {
                "client": args.name,
                "requires": required_features,
                "requires_profiles": [requested_profile],
            },
        },
        "session_start": {
            "id": "session-start-1",
            "method": "akbp.session.start",
            "path": kb_path,
            "params": {
                "task": "current task goals and constraints",
                "limit": 5,
                "max_chars": 4000,
                "min_items": 1,
                "require_citations": True,
            },
        },
        "response_contract": {
            "envelope": {
                "required": ["id", "ok", "result", "error"],
                "id": "matches request id",
                "ok": "boolean",
                "result": "object when ok is true",
                "error": "object when ok is false",
            },
            "success_rules": [
                "Only treat a call as successful when ok is true.",
                "Read structured fields from result instead of parsing stdout prose.",
                "Surface result.context.warnings before relying on retrieved context.",
            ],
            "error_rules": [
                "Branch on error.code, not free-form error.message.",
                "Show error.details when present; it is already redacted by the reference server.",
                "Keep the adapter in read-only mode after capability, doctor, or schema validation failures.",
            ],
            "error_actions": {
                "invalid_json": {
                    "adapter_action": "repair JSON serialization before sending another line",
                    "retry": "after local encoder fix",
                    "write_policy": "never apply approval to malformed JSON",
                },
                "invalid_request": {
                    "adapter_action": "repair the request envelope and remove unknown request-level fields",
                    "retry": "after envelope fix",
                    "write_policy": "never apply approval to envelope failures",
                },
                "unknown_method": {
                    "adapter_action": "refresh akbp.capabilities and disable unavailable flows when still missing",
                    "retry": "only after capability refresh",
                    "write_policy": "do not synthesize replacement method names",
                },
                "invalid_params": {
                    "adapter_action": "repair params using error.details.params_schema, missing fields, unknown fields, and type errors",
                    "retry": "after parameter fix and a fresh dry-run for writes",
                    "write_policy": "do not convert invalid params into an approved write",
                },
                "approval_required": {
                    "adapter_action": "stop the apply path and show the reviewed-write requirement",
                    "retry": "only with approved:true after the exact dry-run request was reviewed",
                    "write_policy": "approval must happen outside the model-generated tool call",
                },
                "cli_error": {
                    "adapter_action": "surface redacted CLI stdout, stderr, and exit code",
                    "retry": "only after the underlying CLI issue is fixed",
                    "write_policy": "do not assume a durable write happened",
                },
                "internal_error": {
                    "adapter_action": "stop the flow and report a server defect",
                    "retry": "do not auto-retry writes",
                    "write_policy": "keep durable writes disabled until the defect is fixed",
                },
            },
            "schemas": {
                "request": "schemas/tool-request.schema.json",
                "response": "schemas/tool-response.schema.json",
                "methods": "schemas/tool-methods.schema.json",
            },
        },
        "health_check": {
            "id": "doctor-1",
            "method": "akbp.doctor",
            "path": kb_path,
            "params": {
                "profile": requested_profile,
            },
            "ready_field": "ready_for_adapter",
            "requested_profile_ready_field": "requested_profile_ready",
            "recommended_profile_field": "adapter_readiness.recommended_profile",
            "security_posture_field": "security_posture",
            "blocking_field": "summary.errors",
        },
        "tool_protocol_bridge": {
            "mode": "reviewed_write" if requested_profile == "reviewed_write" else "read_only",
            "forward_tools": read_only_bridge_tools,
            "host_tool_manifest": host_tool_manifest,
            "client_tool_manifest": client_tool_manifest,
            "read_only_allowlist": [
                "akbp.capabilities",
                "akbp.doctor",
                "akbp.session.start",
                "akbp.context",
                "akbp.search",
                "akbp.cite",
                "akbp.source.verify",
                "akbp.import_check",
            ],
            "blocked_write_methods": [
                "akbp.remember",
                "akbp.source.add",
                "akbp.ingest",
                "akbp.import_apply",
                "akbp.index",
                "akbp.session.end",
                "akbp.crystallize_session",
                "akbp.supersede",
                "akbp.contradict",
            ],
            "reviewed_write_tools": [
                {
                    "tool": "akbp_remember_preview",
                    "method": "akbp.remember",
                    "required_flags": {"dry_run": True},
                },
                {
                    "tool": "akbp_session_end_preview",
                    "method": "akbp.session.end",
                    "required_flags": {"dry_run": True},
                },
                {
                    "tool": "akbp_ingest_preview",
                    "method": "akbp.ingest",
                    "required_flags": {"dry_run": True},
                },
                {
                    "tool": "akbp_apply_reviewed",
                    "method": "same reviewed method/path/params",
                    "required_flags": {"approved": True},
                },
                {
                    "tool": "akbp_index_apply",
                    "method": "akbp.index",
                    "required_flags": {"approved": True},
                },
            ],
            "apply_rule": "Apply only the exact reviewed method, path, and params after approval outside the model-generated tool call.",
            "docs": "docs/TOOL_PROTOCOL_BRIDGE.md",
        },
        "verification": [
            {
                "id": "capabilities-1",
                "run": "startup",
                "expect": {
                    "ok": True,
                    "result.negotiation.satisfied": True,
                    "result.features.method_param_schemas": True,
                    "result.features.method_schema_runtime_parity": True,
                    "result.runtime.method_schema_runtime_errors": [],
                },
                "on_failure": "Disable unsupported flows and show result.negotiation.unsupported_features or unsupported_profiles.",
            },
            {
                "id": "doctor-1",
                "run": "health_check",
                "expect": {
                    "ok": True,
                    "result.requested_profile": requested_profile,
                    "result.requested_profile_ready": True,
                    "result.security_posture.write_boundary": "dry_run_preview_then_approved_apply",
                    f"result.adapter_readiness.{requested_profile}_ready": True,
                    "result.summary.errors": 0,
                },
                "on_failure": "Show result.next_steps, follow result.adapter_readiness.recommended_profile, and keep writes disabled unless reviewed_write_ready is true.",
            },
            {
                "id": "session-start-1",
                "run": "session_start",
                "expect": {
                    "ok": True,
                    "result.context.items": "array",
                    "result.context.warnings": "array",
                    "result.context.budget.max_chars": 4000,
                    "result.quality.minimum_items": 1,
                    "result.quality.require_citations": True,
                },
                "on_failure": "Continue without recalled context and surface the structured error.",
            },
        ],
        "quality_gates": {
            "startup_context": {
                "required_before_planning": requested_profile in {"startup_context", "read_only", "reviewed_write"},
                "minimum_items": 1,
                "require_citations": True,
                "max_chars": 4000,
                "require_budget": True,
                "trust_gate_ref": "adapter_prompt_contract.startup_trust_gate",
                "budget_policy": "request bounded cited context with max_chars; surface budget truncation warnings before relying on recalled memory",
                "warning_policy": "surface result.context.warnings before relying on recalled context",
                "empty_context_policy": "continue without recalled memory; do not invent prior decisions",
                "uncited_context_policy": "treat uncited recalled claims as setup output, not trusted planning input",
                "recommended_harness": "examples/session-start-harness/run.sh",
            },
            "reviewed_writes": {
                "required_for_apply": requested_profile == "reviewed_write",
                "preview_fields": [
                    "review_required",
                    "apply_instruction",
                    "would_write",
                    "warnings",
                ],
                "apply_policy": "repeat the exact reviewed method, path, and params with approved:true only after approval outside the model-generated tool call",
            },
        },
        "maintenance": {
            "purpose": "Keep recalled context trustworthy after setup; storage is easy, stale or unaudited memory is the failure mode.",
            "cadence": {
                "source_verify": "before relying on old citations or before a release",
                "doctor": "after adapter setup changes and before enabling a stricter profile",
                "export_check": "before sharing or importing a portable bundle",
                "index_refresh": "after approved writes when retrieval should include the new records",
            },
            "checks": [
                {
                    "id": "source-verify",
                    "method": "akbp.source.verify",
                    "path": kb_path,
                    "params": {"source_id": "<AKBP_SOURCE_ID>", "fail_on_issue": False},
                    "expected": {
                        "ok": True,
                        "result.counts.changed": 0,
                        "result.counts.missing": 0,
                    },
                    "on_failure": "Surface changed or missing evidence before trusting recalled claims.",
                },
                {
                    "id": "doctor-profile",
                    "method": "akbp.doctor",
                    "path": kb_path,
                    "params": {"limit": 5},
                    "expected": {
                        "ok": True,
                        "result.summary.errors": 0,
                        f"result.adapter_readiness.{requested_profile}_ready": True,
                    },
                    "on_failure": "Show result.next_steps and keep the adapter on the recommended lower-risk profile.",
                },
                {
                    "id": "export-check",
                    "method": "akbp.export_check",
                    "path": kb_path,
                    "params": {"file": "<AKBP_EXPORT_BUNDLE>", "fail_on_issues": True},
                    "expected": {
                        "ok": True,
                        "result.ok": True,
                    },
                    "on_failure": "Do not share or import the bundle until manifest and artifact issues are fixed.",
                },
            ],
            "warning_policy": "Treat source drift, missing evidence, empty startup context, and unsupported workflow profiles as maintenance blockers, not adapter prose.",
        },
        "safety": {
            "profile": requested_profile,
            "write_policy": "dry_run_then_approved" if requested_profile == "reviewed_write" else "no_writes",
            "host_trust_boundary": {
                "default_mode": "read_only_until_verified",
                "hosted_autonomous_tools": "use_read_only_unless_a_separate_human_approval_step_exists",
                "local_interactive_tools": "reviewed_writes_allowed_only_when_previews_are_visible",
            },
            "require_capability_negotiation": True,
            "require_method_param_schemas": True,
            "require_adapter_ready": True,
            "require_human_review_surface": requested_profile == "reviewed_write",
            "require_review_metadata": requested_profile == "reviewed_write",
            "never_auto_apply_session_end": True,
        },
        "notes": [
            "Call startup.method before any other method.",
            "Disable flows when result.negotiation.satisfied is false.",
            "Run health_check.method and show next_steps when ready_field is false.",
            "Keep hosted or autonomous tool integrations read-only unless a separate human approval step exists outside the tool call.",
            "For write-capable flows, preview with dry_run:true and repeat unchanged with approved:true only after review.",
            "Use response_contract to validate envelopes and branch on error.code, not free-form error text.",
        ],
    }
    if args.portable:
        config["distribution"] = {
            "replace_before_run": ["<AKBP_KB_PATH>"],
            "safe_to_commit": True,
            "path_rule": "Keep published adapter templates placeholder-based; resolve the local AKBP path during install or first run.",
        }
    print(json.dumps(config, indent=2))
    return 0


def index_documents(base: Path) -> list[dict[str, str]]:
    docs: list[dict[str, str]] = []
    for claim in load_claims(base):
        cid = str(claim.get("id", ""))
        text = index_text_from_fields(
            claim.get("text"),
            claim.get("type"),
            claim.get("status"),
            claim.get("scope"),
            claim.get("evidence"),
            claim.get("entities"),
        )
        docs.append({
            "doc_key": f"claim:{cid}",
            "kind": "claim",
            "object_id": cid,
            "path": "claims/claims.jsonl",
            "text": text,
            "digest": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        })
    for source in load_sources(base):
        sid = str(source.get("id", ""))
        text = index_text_from_fields(
            source.get("id"),
            source.get("type"),
            source.get("locator"),
            source.get("title"),
            source.get("scope"),
            source.get("hash"),
        )
        docs.append({
            "doc_key": f"source:{sid}",
            "kind": "source",
            "object_id": sid,
            "path": "raw/sources/sources.jsonl",
            "text": text,
            "digest": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        })
    for entity in load_entities(base):
        eid = str(entity.get("id", ""))
        text = index_text_from_fields(
            entity.get("id"),
            entity.get("name"),
            entity.get("type"),
            entity.get("aliases"),
            entity.get("description"),
            entity.get("scope"),
        )
        docs.append({
            "doc_key": f"entity:{eid}",
            "kind": "entity",
            "object_id": eid,
            "path": "graph/entities.jsonl",
            "text": text,
            "digest": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        })
    for relation in load_relations(base):
        rid = str(relation.get("id", ""))
        text = index_text_from_fields(
            relation.get("id"),
            relation.get("source"),
            relation.get("relation"),
            relation.get("target"),
            relation.get("evidence"),
        )
        docs.append({
            "doc_key": f"relation:{rid}",
            "kind": "relation",
            "object_id": rid,
            "path": "graph/relations.jsonl",
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


def index_text_from_fields(*values: Any) -> str:
    parts: list[str] = []
    for value in values:
        if value is None:
            continue
        if isinstance(value, list):
            parts.extend(str(item) for item in value if item is not None)
        elif isinstance(value, dict):
            parts.append(json.dumps(value, ensure_ascii=False, sort_keys=True))
        else:
            parts.append(str(value))
    return "\n".join(part for part in parts if part)


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
        phrase = re.sub(r'[^a-zA-Z0-9_./-]+', ' ', token[1:-1]).strip()
        return '"' + phrase.replace('"', '""') + '"' if phrase else None
    has_prefix = token.endswith("*")
    body = token[:-1] if has_prefix else token
    cleaned = re.sub(r'[^a-zA-Z0-9_./-]+', '', body)
    if not re.search(r'[a-zA-Z0-9_]', cleaned):
        return None
    if has_prefix and re.fullmatch(r'[a-zA-Z0-9_]+', cleaned or ''):
        return cleaned + "*" if cleaned else None
    return '"' + cleaned.replace('"', '""') + '"' if cleaned else None


def fts_query(query: str) -> str:
    raw_tokens = re.findall(r'"[^"]+"|[a-zA-Z0-9_./-]+\*?', query)
    tokens = [(token.upper(), token) for token in raw_tokens if token.strip()]
    operators = {"AND", "OR", "NOT"}
    has_operator = any(upper in operators for upper, _ in tokens)
    if not has_operator:
        cleaned = [term for _, token in tokens if (term := fts_term(token))]
        return " OR ".join(cleaned)

    parts: list[str] = []
    expecting_term = True
    skip_next_term = False
    for upper, token in tokens:
        if upper in {"AND", "OR", "NOT"}:
            if upper == "NOT" and expecting_term:
                skip_next_term = True
                continue
            if not expecting_term:
                parts.append(upper)
                expecting_term = True
            continue
        term = fts_term(token)
        if not term:
            continue
        if skip_next_term:
            skip_next_term = False
            continue
        if not expecting_term:
            parts.append("OR")
        parts.append(term)
        expecting_term = False
    while parts and parts[-1] in operators:
        parts.pop()
    return " ".join(parts)


def cmd_search(args: argparse.Namespace) -> int:
    base = root(args.path)
    db_path = base / ".akbp" / "state.db"
    inactive_matches = inactive_claim_matches(base, args.query, args.limit)
    warnings = []
    if inactive_matches:
        skipped = ", ".join(str(item["id"]) for item in inactive_matches)
        warnings.append(f"Skipped inactive matching claims: {skipped}")
    if not db_path.exists():
        return cmd_query(args)
    query_used = fts_query(args.query)
    if not query_used:
        print(json.dumps({"query": args.query, "backend": "sqlite_fts5", "fts_query": query_used, "results": [], "warnings": warnings}, indent=2, ensure_ascii=False))
        return 0
    results = collect_fts_results(base, args.query, args.limit)
    if results is None:
        return cmd_query(args)
    warnings.extend(source_drift_warnings(base, results, args.limit))
    compact_results = [
        {k: item[k] for k in ("type", "id", "path", "snippet", "rank") if k in item}
        for item in results
    ]
    print(json.dumps({"query": args.query, "backend": "sqlite_fts5", "fts_query": query_used, "results": compact_results, "warnings": warnings}, indent=2, ensure_ascii=False))
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



def is_sha256_hex(value: Any) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"[0-9a-f]{64}", value))


def check_export_bundle_file(bundle_path: Path) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    try:
        raw = bundle_path.read_text(encoding="utf-8", errors="ignore")
    except OSError as exc:
        return {
            "ok": False,
            "file": str(bundle_path),
            "checked_at": now_iso(),
            "issues": [{"code": "file_unreadable", "message": str(exc)}],
            "counts": {"claims": 0, "sources": 0, "entities": 0, "relations": 0},
        }
    if redact_text(raw) != raw:
        issues.append({"code": "secret_like_value", "message": "bundle contains a secret-like value"})
    try:
        bundle = json.loads(raw)
    except json.JSONDecodeError as exc:
        return {
            "ok": False,
            "file": str(bundle_path),
            "checked_at": now_iso(),
            "issues": [*issues, {"code": "invalid_json", "message": exc.msg, "line": exc.lineno, "column": exc.colno}],
            "counts": {"claims": 0, "sources": 0, "entities": 0, "relations": 0},
        }
    if not isinstance(bundle, dict):
        issues.append({"code": "invalid_bundle", "message": "export bundle must be a JSON object"})
        bundle = {}
    for name in ["claims", "sources", "entities", "relations"]:
        if not isinstance(bundle.get(name), list):
            issues.append({"code": "invalid_collection", "message": f"{name} must be an array"})
    counts = {name: len(bundle.get(name)) if isinstance(bundle.get(name), list) else 0 for name in ["claims", "sources", "entities", "relations"]}
    manifest = bundle.get("manifest")
    manifest_format = None
    if not isinstance(manifest, dict):
        issues.append({"code": "missing_manifest", "message": "bundle manifest is required"})
        manifest = {}
    else:
        manifest_format = manifest.get("format")
        if manifest.get("format") != "akbp-portable-bundle":
            issues.append({"code": "invalid_manifest_format", "message": "manifest format must be akbp-portable-bundle"})
        manifest_counts = manifest.get("counts")
        if not isinstance(manifest_counts, dict):
            issues.append({"code": "missing_manifest_counts", "message": "manifest counts are required"})
        else:
            for name, count in counts.items():
                if manifest_counts.get(name) != count:
                    issues.append({"code": "count_mismatch", "message": f"manifest count for {name} does not match bundle", "expected": count, "actual": manifest_counts.get(name)})
        hashes = manifest.get("artifact_hashes")
        if not isinstance(hashes, dict):
            issues.append({"code": "missing_artifact_hashes", "message": "manifest artifact_hashes are required"})
        else:
            for name in ["card", "claims", "sources", "entities", "relations"]:
                value = hashes.get(name)
                if value is not None and not is_sha256_hex(value):
                    issues.append({"code": "invalid_artifact_hash", "message": f"artifact hash for {name} must be a SHA-256 hex string or null"})
        safety = manifest.get("safety")
        if not isinstance(safety, dict):
            issues.append({"code": "missing_safety", "message": "manifest safety flags are required"})
        else:
            for flag in ["excludes_local_state", "excludes_indexes", "secret_redaction_required"]:
                if safety.get(flag) is not True:
                    issues.append({"code": "unsafe_manifest", "message": f"manifest safety flag {flag} must be true"})
    return {
        "ok": not issues,
        "file": str(bundle_path),
        "checked_at": now_iso(),
        "manifest_format": manifest_format,
        "counts": counts,
        "issues": issues,
    }


def cmd_export_check(args: argparse.Namespace) -> int:
    result = check_export_bundle_file(Path(args.file).resolve())
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 1 if args.fail_on_issues and result["issues"] else 0

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
    if not locator:
        print(json.dumps({"ok": False, "error": "source locator is required"}, indent=2), file=sys.stderr)
        return 1
    if args.type == "url" and not locator.lower().startswith(("http://", "https://")):
        print(json.dumps({
            "ok": False,
            "error": "url sources must use an http:// or https:// locator",
        }, indent=2), file=sys.stderr)
        return 1
    source_hash = args.hash
    if source_hash is None and args.type == "file":
        source_hash = file_hash((base / locator).resolve()) or file_hash(Path(locator).resolve())
    safe_title = redact_text(args.title) if args.title else args.title
    source = {
        "id": args.id or stable_id("source", args.type, locator),
        "type": args.type,
        "locator": locator,
        "title": safe_title,
        "hash": source_hash,
        "immutable": not args.mutable,
        "scope": args.scope,
        "created_at": now_iso(),
        "metadata": {},
    }
    append_jsonl(base / "raw" / "sources" / "sources.jsonl", source)
    add_log(base, "source add", f"- Source: `{source['id']}`\n- Locator: {locator}\n")
    audit(base, "source_add", {"source_id": source["id"], "locator": locator, "redacted": bool(args.title and args.title != safe_title)})
    auto_index_if_present(base)
    print(json.dumps(source, indent=2, ensure_ascii=False))
    return 0



def resolve_source_file(base: Path, locator: str) -> Path:
    candidate = Path(locator)
    if candidate.is_absolute():
        return candidate
    base_candidate = (base / locator).resolve()
    if base_candidate.exists():
        return base_candidate
    return candidate.resolve()


def verify_sources(base: Path, source_id: str | None = None) -> dict[str, Any]:
    sources = load_sources(base)
    if source_id:
        sources = [source for source in sources if source.get("id") == source_id]
        if not sources:
            missing_item = {
                "id": source_id,
                "type": "",
                "locator": "",
                "affected_claims": [],
                "reason": "source_not_found",
            }
            return {
                "ok": False,
                "checked_at": now_iso(),
                "source_id": source_id,
                "counts": {
                    "checked": 0,
                    "verified": 0,
                    "changed": 0,
                    "missing": 1,
                    "unchecked": 0,
                },
                "verified": [],
                "changed": [],
                "missing": [missing_item],
                "unchecked": [],
                "attention": {
                    "requires_review": True,
                    "recommended_action": "review_sources",
                    "changed_source_ids": [],
                    "missing_source_ids": [source_id],
                    "affected_claims": [],
                },
            }
    affected_claims = affected_claims_by_evidence(base)
    verified: list[dict[str, Any]] = []
    changed: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    unchecked: list[dict[str, Any]] = []
    for source in sources:
        sid = str(source.get("id") or "")
        stype = str(source.get("type") or "")
        locator = str(source.get("locator") or "")
        expected = source.get("hash")
        affected = sorted(set(affected_claims.get(sid, []) + affected_claims.get(locator, [])))
        base_item = {"id": sid, "type": stype, "locator": locator, "affected_claims": affected}
        if stype != "file":
            unchecked.append({**base_item, "reason": "non_file_source"})
            continue
        if not expected:
            unchecked.append({**base_item, "reason": "missing_recorded_hash"})
            continue
        path = resolve_source_file(base, locator)
        actual = file_hash(path)
        if actual is None:
            missing.append({**base_item, "expected_hash": expected})
        elif actual == expected:
            verified.append({**base_item, "hash": actual})
        else:
            changed.append({**base_item, "expected_hash": expected, "actual_hash": actual})
    affected_attention = sorted({
        claim_id
        for item in changed + missing
        for claim_id in item.get("affected_claims", [])
        if isinstance(claim_id, str) and claim_id
    })
    attention_action = "none"
    if changed or missing:
        attention_action = "review_affected_claims" if affected_attention else "review_sources"
    return {
        "ok": not changed and not missing,
        "checked_at": now_iso(),
        "source_id": source_id,
        "counts": {
            "checked": len(sources),
            "verified": len(verified),
            "changed": len(changed),
            "missing": len(missing),
            "unchecked": len(unchecked),
        },
        "verified": verified,
        "changed": changed,
        "missing": missing,
        "unchecked": unchecked,
        "attention": {
            "requires_review": bool(changed or missing),
            "recommended_action": attention_action,
            "changed_source_ids": [item["id"] for item in changed],
            "missing_source_ids": [item["id"] for item in missing],
            "affected_claims": affected_attention,
        },
    }


def affected_claims_by_evidence(base: Path) -> dict[str, list[str]]:
    affected: dict[str, list[str]] = {}
    for claim in load_claims(base):
        claim_id = str(claim.get("id") or "")
        if not claim_id:
            continue
        for evidence_id in claim.get("evidence", []) or []:
            if isinstance(evidence_id, str) and evidence_id:
                affected.setdefault(evidence_id, []).append(claim_id)
    for claim_ids in affected.values():
        claim_ids.sort()
    return affected


def cmd_source_verify(args: argparse.Namespace) -> int:
    base = root(args.path)
    result = verify_sources(base, args.source_id)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 1 if args.fail_on_issue and not result["ok"] else 0

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
    s.add_argument(
        "--level",
        default="0",
        choices=["0"],
        help="initialize a Level 0 AKBP file-convention knowledge base",
    )
    s.set_defaults(func=cmd_init)

    s = sub.add_parser("discover", help="find the nearest AKBP knowledge base from --path or its parents")
    s.set_defaults(func=cmd_discover)

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
    s.add_argument("--max-chars", type=int, help="cap total context item summary characters")
    s.add_argument("--min-items", type=int, default=0, help="fail when fewer context items are returned")
    s.add_argument("--require-citations", action="store_true", help="fail when returned context items lack citations")
    s.add_argument("--fail-on-warnings", action="store_true", help="fail when the context pack includes warnings")
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

    s = sub.add_parser("export-check")
    s.add_argument("file")
    s.add_argument("--fail-on-issues", action="store_true")
    s.set_defaults(func=cmd_export_check)

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
    s_verify = source_sub.add_parser("verify")
    s_verify.add_argument("source_id", nargs="?")
    s_verify.add_argument("--fail-on-issue", action="store_true")
    s_verify.set_defaults(func=cmd_source_verify)

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
    s.add_argument("--dry-run", action="store_true", help="preview session extraction without writing durable artifacts")
    s.set_defaults(func=cmd_crystallize)

    s = sub.add_parser("lint")
    s.set_defaults(func=cmd_lint)

    s = sub.add_parser("conformance")
    s.add_argument("--level", default="0", choices=["0", "1", "2", "3", "4", "5"])
    s.set_defaults(func=cmd_conformance)

    s = sub.add_parser("status")
    s.add_argument("--limit", type=int, default=5, help="number of recent claims and source issues to include")
    s.set_defaults(func=cmd_status)

    s = sub.add_parser("doctor")
    s.add_argument("--limit", type=int, default=5, help="number of next steps to include")
    s.add_argument(
        "--profile",
        choices=["startup-context", "read-only", "reviewed-writes"],
        help="also fail when the requested adapter workflow profile is not ready",
    )
    s.set_defaults(func=cmd_doctor)

    s = sub.add_parser("client-config", help="print a stdio JSONL client configuration for the AKBP tool server")
    s.add_argument("--name", default="akbp-client", help="client name to use during capability negotiation")
    s.add_argument("--profile", choices=["startup-context", "read-only", "reviewed-writes"], default="read-only")
    s.add_argument("--command", choices=["console", "python-module", "repo-script"], default="console")
    s.add_argument("--portable", action="store_true", help="emit a commit-safe template with <AKBP_KB_PATH> instead of an absolute path")
    s.set_defaults(func=cmd_client_config)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
