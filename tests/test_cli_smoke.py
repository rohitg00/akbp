import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "cli" / "akbp.py"


def run(*args, cwd=None):
    return subprocess.run([sys.executable, str(CLI), *args], cwd=cwd, text=True, capture_output=True, check=True)


def test_init_remember_query_lint():
    with tempfile.TemporaryDirectory() as d:
        kb = Path(d) / "kb"
        run("--path", str(kb), "init")
        assert (kb / "wiki" / "index.md").exists()
        out = run("--path", str(kb), "remember", "This project uses Bun instead of npm", "--type", "decision", "--evidence", "README.md")
        claim = json.loads(out.stdout)
        assert claim["type"] == "decision"
        out = run("--path", str(kb), "query", "Bun npm")
        results = json.loads(out.stdout)["results"]
        assert results
        out = run("--path", str(kb), "lint")
        assert json.loads(out.stdout)["ok"] is True
