#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

KB="$TMP/kb"
STALE="examples/context-compaction-recovery/stale-relative-date-memory.md"
CURRENT="examples/context-compaction-recovery/compaction-review.md"

echo "AKBP context compaction recovery example"

python3 "$ROOT/cli/akbp.py" --path "$KB" init >/dev/null
python3 "$ROOT/cli/akbp.py" --path "$KB" source add "$ROOT/$STALE" --type file --title "Stale relative-date memory note" >/dev/null
python3 "$ROOT/cli/akbp.py" --path "$KB" source add "$ROOT/$CURRENT" --type file --title "Compaction handoff review" >/dev/null

STALE_JSON=$(python3 "$ROOT/cli/akbp.py" --path "$KB" remember \
  "After compaction, agents can continue from yesterday's memory note without citations because the chat transcript still has enough context." \
  --type workflow \
  --confidence 0.38 \
  --evidence "$ROOT/$STALE" \
  --entity context-compaction \
  --entity relative-dates)
STALE_CLAIM=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])' <<<"$STALE_JSON")

CURRENT_JSON=$(python3 "$ROOT/cli/akbp.py" --path "$KB" supersede "$STALE_CLAIM" \
  "After a context compaction, adapters should retrieve a cited AKBP handoff snapshot with absolute dates, source ids, lifecycle status, and review-gated next actions before planning." \
  --type workflow \
  --confidence 0.92 \
  --evidence "$ROOT/$CURRENT" \
  --entity context-compaction \
  --entity handoff \
  --entity absolute-dates \
  --entity citations \
  --entity lifecycle)
CURRENT_CLAIM=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])' <<<"$CURRENT_JSON")

python3 "$ROOT/cli/akbp.py" --path "$KB" index --incremental >/dev/null

python3 "$ROOT/tool-server/akbp_tool_server.py" <<JSONL | CURRENT_CLAIM="$CURRENT_CLAIM" STALE_CLAIM="$STALE_CLAIM" python3 -c '
import json
import os
import sys

rows = [json.loads(line) for line in sys.stdin if line.strip()]
by_id = {row["id"]: row for row in rows}

caps = by_id["caps"]
assert caps["ok"], caps
assert "startup_context" in caps["result"]["negotiation"]["supported_profiles"], caps

start = by_id["start"]
assert start["ok"], start
context = start["result"]["context"]
assert context["quality"]["ok"], context
assert context["budget"]["max_chars"] == 650, context["budget"]
assert context["budget"]["truncated"] is False, context["budget"]

items = context["items"]
ids = [item["id"] for item in items]
assert os.environ["CURRENT_CLAIM"] in ids, ids
assert ids[0] == os.environ["CURRENT_CLAIM"], ids
assert all(item["freshness"] != "superseded" for item in items[:1]), items

current = items[0]
assert current["citations"], current
assert "absolute dates" in current["summary"], current
assert "review-gated" in current["summary"], current

print("compaction startup context ok")
'
{"id":"caps","method":"akbp.capabilities","path":"$KB","params":{"client":"context-compaction-recovery-example","requires":["method_param_schemas","capability_negotiation"],"requires_profiles":["startup_context"]}}
{"id":"start","method":"akbp.session.start","path":"$KB","params":{"task":"resume after context compaction with cited handoff snapshot absolute dates lifecycle","limit":5,"max_chars":650}}
JSONL

python3 "$ROOT/cli/akbp.py" --path "$KB" conformance --level 3 >/dev/null

echo "AKBP context compaction recovery example passed"
