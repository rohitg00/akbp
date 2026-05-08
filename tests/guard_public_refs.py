from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BANNED = [
    "AGENTS.md",
    "Model Context Protocol",
    "modelcontextprotocol",
    "MCP",
    "Agent2Agent",
    "A2A",
    "agentsmd",
    "GBrain",
    "gbrain",
    "mirage",
    "Mirage",
    "virtual filesystem",
    "Virtual Filesystem",
]
SKIP_PARTS = {".git", "build", "dist", "__pycache__"}
SKIP_SUFFIXES = {".pyc"}
ALLOW_FILES = {Path("tests/guard_public_refs.py")}

violations: list[str] = []
for path in ROOT.rglob("*"):
    rel = path.relative_to(ROOT)
    if any(part in SKIP_PARTS for part in rel.parts) or path.suffix in SKIP_SUFFIXES or rel in ALLOW_FILES:
        continue
    if path.is_file():
        text = path.read_text(encoding="utf-8", errors="ignore")
        for token in BANNED:
            if token in text:
                violations.append(f"{rel}: contains {token}")
    for token in ["mcp", "a2a", "agents.md"]:
        if token in path.name.lower():
            violations.append(f"{rel}: path contains {token}")
if violations:
    print("\n".join(violations))
    sys.exit(1)
