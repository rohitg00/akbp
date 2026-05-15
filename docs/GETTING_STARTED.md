# Getting started

Use this path when you want to understand AKBP as a working agent-knowledge protocol, not only as a repository of schemas and commands.

## What you should prove in ten minutes

By the end of the first run, you should have seen AKBP do seven things:

1. Create a local knowledge base.
2. Register source material as evidence.
3. Preview a durable memory write before applying it.
4. Reject an unapproved write.
5. Retrieve cited context for a later agent session.
6. Supersede stale knowledge without deleting history.
7. Export and check a portable bundle.

That is the core user value: agents can propose project memory, but durable knowledge stays local, reviewable, cited, and portable.

## Fast path

From a clean checkout:

```bash
git clone https://github.com/rohitg00/akbp.git
cd akbp
make demo
```

The demo creates a temporary knowledge base, adds evidence, writes a reviewed decision, verifies sources, builds search, retrieves context, supersedes stale knowledge, exports a bundle, checks the bundle, and runs level 3 conformance.

Expected success markers:

```text
AKBP quickstart demo
"verified": 1
"results": [
"items": [
"supersedes": [
"event": "supersede"
"ok": true
AKBP quickstart demo passed
```

If this fails, use `docs/TROUBLESHOOTING.md` before debugging the protocol itself.

## Manual path

Use the manual path when you want to see the files AKBP creates.

```bash
TMP_KB="$(mktemp -d)/akbp-first-run"
python3 cli/akbp.py --path "$TMP_KB" init
printf '%s\n' "Release work should stay small, reviewed, and evidence-backed." > "$TMP_KB/session-note.md"
python3 cli/akbp.py --path "$TMP_KB" source add "$TMP_KB/session-note.md" --type file --title "Session note"
python3 cli/akbp.py --path "$TMP_KB" ingest "$TMP_KB/session-note.md" --claim "Release work should stay small, reviewed, and evidence-backed." --claim-type decision
python3 cli/akbp.py --path "$TMP_KB" source verify --fail-on-issue
python3 cli/akbp.py --path "$TMP_KB" index --incremental
python3 cli/akbp.py --path "$TMP_KB" status
python3 cli/akbp.py --path "$TMP_KB" context "prepare the next release"
CLAIM_ID="$(python3 -c 'import json, pathlib; print(json.loads(pathlib.Path("'"$TMP_KB"'/claims/claims.jsonl").read_text().splitlines()[0])["id"])')"
python3 cli/akbp.py --path "$TMP_KB" supersede "$CLAIM_ID" "Release work should stay small, reviewed, evidence-backed, and cadence-flexible." --type decision
python3 cli/akbp.py --path "$TMP_KB" audit --event supersede --limit 5
python3 cli/akbp.py --path "$TMP_KB" export --output "$TMP_KB/export.json"
python3 cli/akbp.py --path "$TMP_KB" export-check "$TMP_KB/export.json"
```

Then inspect the durable artifacts:

```bash
find "$TMP_KB" -maxdepth 3 -type f | sort
sed -n '1,120p' "$TMP_KB/claims/claims.jsonl"
sed -n '1,120p' "$TMP_KB/raw/sources/sources.jsonl"
```

The important distinction is that `.akbp/` is rebuildable runtime state. The portable state is the markdown and JSONL artifact set.

`akbp status` is the quick health check for a knowledge base. It keeps the old object counts, and also returns dashboard-ready sections for latest claims, claim type/status counts, source verification health, audit count, index presence, and highest passing conformance level.

## Agent write-safety path

Use the JSONL tool server to see how an adapter should behave.

```bash
TMP_KB="$(mktemp -d)/akbp-tool-first-run"
python3 cli/akbp.py --path "$TMP_KB" init

printf '%s\n' \
  '{"id":"preview","method":"akbp.remember","path":"'"$TMP_KB"'","dry_run":true,"params":{"text":"Decision: release notes must link to validation evidence.","type":"decision"}}' \
  '{"id":"blocked","method":"akbp.remember","path":"'"$TMP_KB"'","params":{"text":"Unreviewed durable writes should be rejected.","type":"policy"}}' \
  '{"id":"approved","method":"akbp.remember","path":"'"$TMP_KB"'","approved":true,"params":{"text":"Decision: release notes must link to validation evidence.","type":"decision"}}' \
  '{"id":"status","method":"akbp.status","path":"'"$TMP_KB"'","params":{"limit":3}}' \
  '{"id":"ctx","method":"akbp.context","path":"'"$TMP_KB"'","params":{"task":"prepare release notes","limit":5}}' \
  | python3 tool-server/akbp_tool_server.py
```

Expected behavior:

- `preview` succeeds without writing durable claims and returns review metadata.
- `blocked` fails with `error.code:"approval_required"`.
- `approved` writes only because request-level approval is explicit.
- `status` returns counts, latest claims, source health, index presence, and conformance.
- `ctx` returns later-session context from the approved knowledge base.

This is the adapter contract in one minute: retrieve before planning, dry-run before writing, require approval before durable memory, then recall cited context next session.

## Choose your next path

- New user: run `make demo`, then read `docs/AKBP_WORKFLOW.md`.
- Adapter author: read `docs/ADAPTER_AUTHOR_QUICKSTART.md`, then inspect `examples/adapter-lifecycle/`.
- Protocol reviewer: read `docs/ARCHITECTURE.md`, `docs/TOOL_CONTRACT.md`, and `schemas/`.
- Skeptical reviewer: run `make benchmark`, then read `docs/CRITIQUE_RESPONSE.md`.
- Release reviewer: run `make validate`, then read `docs/RELEASE.md`.

## What AKBP is optimizing for

AKBP is not trying to be another opaque memory app. It is optimizing for a portable contract that different agents can share:

- local files as the source of truth
- source-backed claims
- dry-run previews
- explicit approval for writes
- cited context recall
- lifecycle updates such as supersession and contradiction
- export bundles that another tool can inspect before import

If an integration hides those properties, it is probably using AKBP as a storage layer but missing the protocol.
