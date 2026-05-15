#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

KB="$TMP/kb"
NOTE="$TMP/inherited-repo-note.md"
UNSAFE_IMPORT="$TMP/unsafe-import.jsonl"

echo "AKBP source intake example"

python3 "$ROOT/cli/akbp.py" --path "$KB" init >/dev/null

cat > "$NOTE" <<'NOTE'
# Inherited repo intake

Decision: agents taking over an inherited repository should retrieve cited startup context before changing durable project memory.
NOTE

python3 "$ROOT/cli/akbp.py" --path "$KB" source add "$NOTE" --type file --title "Inherited repo intake note" >/dev/null

INGEST_REQUEST='{"file":"'"$NOTE"'","type":"file","title":"Inherited repo intake note","claim":"Agents taking over an inherited repository should retrieve cited startup context before changing durable project memory.","claim_type":"workflow"}'

TOOL_JSON="$(printf '%s\n' \
  '{"id":"caps","method":"akbp.capabilities","path":"'"$KB"'","params":{"client":"source-intake-example","requires":["method_param_schemas","capability_negotiation","write_apply_requires_approval"]}}' \
  '{"id":"ingest-preview","method":"akbp.ingest","path":"'"$KB"'","dry_run":true,"params":'"$INGEST_REQUEST"'}' \
  '{"id":"ingest-blocked","method":"akbp.ingest","path":"'"$KB"'","params":'"$INGEST_REQUEST"'}' \
  '{"id":"ingest-approved","method":"akbp.ingest","path":"'"$KB"'","approved":true,"params":'"$INGEST_REQUEST"'}' \
  '{"id":"index-approved","method":"akbp.index","path":"'"$KB"'","approved":true,"params":{"incremental":true}}' \
  '{"id":"start","method":"akbp.session.start","path":"'"$KB"'","params":{"task":"take over an inherited repository safely","limit":5}}' \
  | python3 "$ROOT/tool-server/akbp_tool_server.py")"

printf '%s\n' "$TOOL_JSON" | python3 -c '
import json, sys

rows = [json.loads(line) for line in sys.stdin if line.strip()]
by_id = {row["id"]: row for row in rows}

caps = by_id["caps"]["result"]
assert caps["negotiation"]["satisfied"], caps
assert caps["features"]["write_apply_requires_approval"], caps

preview = by_id["ingest-preview"]["result"]
assert preview["dry_run"], preview
assert preview["review_required"], preview
assert preview["would_write"], preview

blocked = by_id["ingest-blocked"]
assert not blocked["ok"], blocked
assert blocked["error"]["code"] == "approval_required", blocked

approved = by_id["ingest-approved"]["result"]
assert approved["created_claims"], approved
assert approved["source_id"], approved

indexed = by_id["index-approved"]["result"]
assert indexed["indexed"] >= 1, indexed

start = by_id["start"]["result"]
assert start["context"]["items"], start
assert "retrieve cited startup context" in json.dumps(start), start

print("review-gated source intake ok")
'

cat > "$UNSAFE_IMPORT" <<'JSONL'
{"kind":"claim","id":"claim_unsafe_intake","text":"Token ghp_example_secret_should_not_import belongs in memory.","type":"fact","status":"stable","confidence":0.9,"evidence":[]}
JSONL

python3 "$ROOT/cli/akbp.py" --path "$KB" import-check "$UNSAFE_IMPORT" --fail-on-rejected >/dev/null 2>&1 && {
  echo "unsafe import unexpectedly passed" >&2
  exit 1
}

python3 "$ROOT/cli/akbp.py" --path "$KB" context "safe inherited repo intake" | python3 -c '
import json, sys
data = json.load(sys.stdin)
assert data["items"], data
assert data["items"][0]["citations"], data
print("cited intake context ok")
'

echo "AKBP source intake example passed"
