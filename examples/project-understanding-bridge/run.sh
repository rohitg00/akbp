#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

KB="$TMP/kb"
NOTE="$TMP/project-understanding.md"
CONFIG="$TMP/project-understanding-client-config.json"
BUNDLE="$TMP/project-understanding-bridge-bundle.json"

echo "AKBP project understanding bridge example"

python3 "$ROOT/cli/akbp.py" --path "$KB" init >/dev/null

cat > "$NOTE" <<'NOTE'
# Project understanding

Decision: keep checkout recovery changes small and backed by a smoke test.
Workflow: before editing payment retry behavior, inspect queue backoff and idempotency-key logs together.
Scratchpad: revisit dashboard colors later if this becomes customer-facing.
NOTE

SOURCE_JSON="$(python3 "$ROOT/cli/akbp.py" --path "$KB" source add "$NOTE" --type file --title "Project understanding scratchpad")"
SOURCE_ID="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])' <<<"$SOURCE_JSON")"

python3 "$ROOT/cli/akbp.py" --path "$KB" client-config --name project-understanding-bridge --profile read-only > "$CONFIG"
python3 -c '
import json
import sys

config = json.load(open(sys.argv[1], encoding="utf-8"))
fit = config["memory_landscape_fit"]
comparison = fit["plain_markdown_cache_comparison"]
assert comparison["format"] == "akbp-plain-markdown-cache-comparison-v1", comparison
assert "temporary scratchpad context" in comparison["use_plain_markdown_or_cache_when"][0], comparison
assert "cited before future agents plan" in comparison["use_akbp_when"][0], comparison
assert "approval_required" in comparison["minimum_proof"][1], comparison
print("plain markdown comparison contract ok")
' "$CONFIG"

printf '%s\n' \
  '{"id":"caps","method":"akbp.capabilities","path":"'"$KB"'","params":{"client":"project-understanding-bridge","requires":["method_param_schemas","capability_negotiation","write_apply_requires_approval"],"requires_profiles":["read_only","startup_context","portability"]}}' \
  '{"id":"preview-decision","method":"akbp.remember","path":"'"$KB"'","dry_run":true,"params":{"text":"Checkout recovery changes should stay small and be backed by a smoke test.","type":"decision","evidence":["'"$SOURCE_ID"'"]}}' \
  '{"id":"blocked-workflow","method":"akbp.remember","path":"'"$KB"'","params":{"text":"Payment retry changes should inspect queue backoff and idempotency-key logs together before editing retry behavior.","type":"workflow","evidence":["'"$SOURCE_ID"'"]}}' \
  '{"id":"approved-decision","method":"akbp.remember","path":"'"$KB"'","approved":true,"params":{"text":"Checkout recovery changes should stay small and be backed by a smoke test.","type":"decision","evidence":["'"$SOURCE_ID"'"]}}' \
  '{"id":"approved-workflow","method":"akbp.remember","path":"'"$KB"'","approved":true,"params":{"text":"Payment retry changes should inspect queue backoff and idempotency-key logs together before editing retry behavior.","type":"workflow","evidence":["'"$SOURCE_ID"'"]}}' \
  '{"id":"verify-source","method":"akbp.source.verify","path":"'"$KB"'","params":{"source_id":"'"$SOURCE_ID"'","fail_on_issue":true}}' \
  '{"id":"index","method":"akbp.index","path":"'"$KB"'","approved":true,"params":{"incremental":true}}' \
  '{"id":"start","method":"akbp.session.start","path":"'"$KB"'","params":{"task":"change payment retry behavior safely","limit":5,"require_citations":true,"fail_on_warnings":true}}' \
  '{"id":"export","method":"akbp.export","path":"'"$KB"'"}' \
  | python3 "$ROOT/tool-server/akbp_tool_server.py" \
  | python3 -c '
import json
import sys
from pathlib import Path

rows = [json.loads(line) for line in sys.stdin if line.strip()]
by_id = {row["id"]: row for row in rows}

assert by_id["caps"]["ok"], by_id["caps"]
negotiation = by_id["caps"]["result"]["negotiation"]
assert negotiation["satisfied"], negotiation

preview = by_id["preview-decision"]
assert preview["ok"], preview
assert preview["result"]["dry_run"], preview
assert preview["result"]["review_required"], preview
assert preview["result"]["would_write"], preview

blocked = by_id["blocked-workflow"]
assert not blocked["ok"], blocked
assert blocked["error"]["code"] == "approval_required", blocked

approved = [by_id["approved-decision"], by_id["approved-workflow"]]
assert all(row["ok"] for row in approved), approved
assert all(row["result"]["evidence"] for row in approved), approved
print("review-gated promotion from markdown ok")

verified = by_id["verify-source"]["result"]
assert verified["ok"], verified
assert verified["changed"] == [], verified
assert verified["missing"] == [], verified
assert verified["verified"][0]["affected_claims"], verified
print("plain markdown registered as evidence ok")

indexed = by_id["index"]["result"]
assert indexed["indexed"] >= 2, indexed

context = by_id["start"]["result"]["context"]
assert context["items"], context
assert all(item["citations"] for item in context["items"]), context
payload = json.dumps(context)
assert "Payment retry" in payload or "payment retry" in payload, payload
assert "queue backoff" in payload, payload
print("cited startup context from promoted markdown ok")

exported = by_id["export"]["result"]
assert exported["manifest"]["counts"]["claims"] >= 2, exported
assert exported["manifest"]["safety"]["excludes_local_state"], exported
Path("'"$BUNDLE"'").write_text(json.dumps(exported, indent=2, sort_keys=True) + "\n", encoding="utf-8")
'

printf '%s\n' '{"id":"export-check","method":"akbp.export_check","path":"'"$KB"'","params":{"file":"'"$BUNDLE"'","fail_on_issues":true}}' \
  | python3 "$ROOT/tool-server/akbp_tool_server.py" \
  | python3 -c '
import json
import sys

row = json.loads(sys.stdin.readline())
assert row["ok"], row
assert row["result"]["ok"], row
assert row["result"]["issues"] == [], row
print("portable bridge export-check ok")
'

echo "AKBP project understanding bridge example passed"
