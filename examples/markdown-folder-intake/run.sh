#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

KB="$TMP/kb"
NOTES="$TMP/agent-notes"

echo "AKBP markdown folder intake example"

mkdir -p "$NOTES"

cat > "$NOTES/adr-cache-policy.md" <<'NOTE'
# ADR draft: cache policy

Decision: API cache entries must expire after 10 minutes unless a route-specific runbook says otherwise.
Evidence: the payment retry worker produced stale status pages during the last incident review.
NOTE

cat > "$NOTES/debugging-payment-retries.md" <<'NOTE'
# Debugging note: payment retries

Workflow: before changing payment retry behavior, inspect the queue backoff setting and the idempotency-key log together.
Evidence: earlier single-file fixes missed duplicate retry paths.
NOTE

python3 "$ROOT/cli/akbp.py" --path "$KB" init >/dev/null

declare -a REQUESTS=(
  '{"id":"caps","method":"akbp.capabilities","path":"'"$KB"'","params":{"client":"markdown-folder-intake-example","requires":["method_param_schemas","write_apply_requires_approval"]}}'
)

while IFS= read -r note; do
  title="$(basename "$note" .md | tr '-' ' ')"
  source_json="$(python3 "$ROOT/cli/akbp.py" --path "$KB" source add "$note" --type file --title "$title")"
  source_id="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])' <<<"$source_json")"
  case "$(basename "$note")" in
    adr-cache-policy.md)
      claim="API cache entries must expire after 10 minutes unless route-specific runbooks override the default."
      claim_type="decision"
      ;;
    debugging-payment-retries.md)
      claim="Payment retry changes should inspect queue backoff and idempotency-key logs together before editing retry behavior."
      claim_type="workflow"
      ;;
    *)
      echo "unexpected note $note" >&2
      exit 1
      ;;
  esac
  params="$(python3 -c 'import json,sys; print(json.dumps({"text": sys.argv[1], "type": sys.argv[2], "evidence": [sys.argv[3]]}))' "$claim" "$claim_type" "$source_id")"
  base="$(basename "$note" .md)"
  REQUESTS+=(
    '{"id":"remember-preview-'"$base"'","method":"akbp.remember","path":"'"$KB"'","dry_run":true,"params":'"$params"'}'
    '{"id":"remember-blocked-'"$base"'","method":"akbp.remember","path":"'"$KB"'","params":'"$params"'}'
    '{"id":"remember-approved-'"$base"'","method":"akbp.remember","path":"'"$KB"'","approved":true,"params":'"$params"'}'
  )
done < <(find "$NOTES" -type f -name '*.md' | sort)

REQUESTS+=(
  '{"id":"index-approved","method":"akbp.index","path":"'"$KB"'","approved":true,"params":{"incremental":true}}'
  '{"id":"start","method":"akbp.session.start","path":"'"$KB"'","params":{"task":"change payment retry behavior without stale cache assumptions","limit":5,"require_citations":true,"fail_on_warnings":true}}'
)

TOOL_JSON="$(printf '%s\n' "${REQUESTS[@]}" | python3 "$ROOT/tool-server/akbp_tool_server.py")"

printf '%s\n' "$TOOL_JSON" | python3 -c '
import json
import sys

rows = [json.loads(line) for line in sys.stdin if line.strip()]
by_id = {row["id"]: row for row in rows}

caps = by_id["caps"]["result"]
assert caps["negotiation"]["satisfied"], caps
assert caps["features"]["method_param_schemas"], caps
assert caps["features"]["write_apply_requires_approval"], caps

approved_claims = []
for key, row in by_id.items():
    if key.startswith("remember-preview-"):
        result = row["result"]
        assert result["dry_run"], result
        assert result["review_required"], result
        assert result["would_write"], result
    if key.startswith("remember-blocked-"):
        assert row["ok"] is False, row
        assert row["error"]["code"] == "approval_required", row
    if key.startswith("remember-approved-"):
        result = row["result"]
        assert result["id"], result
        assert result["evidence"], result
        approved_claims.append(result["id"])

assert len(approved_claims) == 2, approved_claims
print("registered markdown sources ok")
print("review-gated markdown promotion ok")

indexed = by_id["index-approved"]["result"]
assert indexed["indexed"] >= 2, indexed

context = by_id["start"]["result"]["context"]
assert context["items"], context
assert all(item["citations"] for item in context["items"]), context
payload = json.dumps(context)
assert "queue backoff" in payload, payload
assert "cache entries" in payload, payload
print("cited markdown context ok")
'

echo "AKBP markdown folder intake example passed"
