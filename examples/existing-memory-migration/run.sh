#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

KB="$TMP/migrated-kb"
INCOMING="$TMP/existing-memory-export.jsonl"
BAD_INCOMING="$TMP/bad-existing-memory-export.jsonl"
OPAQUE_INCOMING="$TMP/opaque-host-memory-export.jsonl"

echo "AKBP existing memory migration example"

python3 "$ROOT/cli/akbp.py" --path "$KB" init >/dev/null

cat > "$INCOMING" <<'JSONL'
{"kind":"source","id":"source_existing_memory_note","type":"note","locator":"memory-export/session-policy.md","title":"Existing memory session policy"}
{"kind":"claim","id":"claim_existing_memory_session_policy","text":"Project memory updates must be reviewed at session boundaries.","type":"policy","status":"working","confidence":0.82,"evidence":["source_existing_memory_note"],"scope":"project"}
JSONL

cat > "$BAD_INCOMING" <<'JSONL'
{"kind":"claim","id":"claim_missing_source","text":"Claims without source records should not migrate.","type":"policy","status":"working","confidence":0.4,"evidence":["source_missing_memory_note"],"scope":"project"}
JSONL

cat > "$OPAQUE_INCOMING" <<'JSONL'
{"kind":"claim","id":"claim_opaque_host_summary","text":"Hosted memory summaries need source review before durable AKBP import.","type":"workflow","status":"working","confidence":0.55,"scope":"project"}
JSONL

python3 "$ROOT/cli/akbp.py" --path "$KB" import-check "$BAD_INCOMING" | python3 -c 'import json,sys; data=json.load(sys.stdin); assert data["ok"]; assert data["rejected_count"] == 1; assert data["accepted_count"] == 0; assert data["rejected"][0]["reason"].startswith("unknown evidence source id"); assert not data["review"]["ready_for_reviewed_apply"]; print("bad migration rejected")'
python3 "$ROOT/cli/akbp.py" --path "$KB" import-check "$OPAQUE_INCOMING" --fail-on-rejected | python3 -c 'import json,sys; data=json.load(sys.stdin); assert data["ok"]; assert data["accepted_count"] == 1; assert data["rejected_count"] == 0; assert not data["review"]["ready_for_reviewed_apply"]; assert data["review"]["claims_without_evidence"] == ["claim_opaque_host_summary"]; assert any("source evidence" in action for action in data["review"]["next_actions"]); print("opaque host summary needs source review")'
python3 "$ROOT/cli/akbp.py" --path "$KB" import-check "$INCOMING" --fail-on-rejected | python3 -c 'import json,sys; data=json.load(sys.stdin); assert data["ok"]; assert data["accepted_count"] == 2; assert data["rejected_count"] == 0; assert data["review"]["ready_for_reviewed_apply"]; assert data["review"]["source_count"] == 1; assert data["review"]["claim_count"] == 1; assert data["review"]["claims_without_evidence"] == []; assert data["review"]["claims_without_source_evidence"] == []; print("migration check ok")'
python3 "$ROOT/cli/akbp.py" --path "$KB" import-apply "$INCOMING" --dry-run | python3 -c 'import json,sys; data=json.load(sys.stdin); assert data["ok"]; assert data["dry_run"]; assert data["review_required"]; assert data["would_write"]["sources"] == ["source_existing_memory_note"]; assert data["would_write"]["claims"] == ["claim_existing_memory_session_policy"]; assert data["review"]["ready_for_reviewed_apply"]; print("migration preview ok")'
python3 "$ROOT/cli/akbp.py" --path "$KB" import-apply "$INCOMING" --approved | python3 -c 'import json,sys; data=json.load(sys.stdin); assert data["ok"]; assert data["applied"]; assert data["would_write"]["sources"] == ["source_existing_memory_note"]; assert data["would_write"]["claims"] == ["claim_existing_memory_session_policy"]; assert data["skipped_existing"]["sources"] == []; assert data["skipped_existing"]["claims"] == []; print("migration apply ok")'
python3 "$ROOT/cli/akbp.py" --path "$KB" index --incremental >/dev/null
python3 "$ROOT/cli/akbp.py" --path "$KB" context "prepare the next agent session memory update" | python3 -c 'import json,sys; data=json.load(sys.stdin); text=json.dumps(data); assert "reviewed at session boundaries" in text; assert "claim_existing_memory_session_policy" in text; print("migration recall ok")'

echo "AKBP existing memory migration example passed"
