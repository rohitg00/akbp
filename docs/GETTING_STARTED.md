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

## What gets created

AKBP is easiest to evaluate when the first run makes the file contract visible. A new knowledge base starts small:

| Artifact | Purpose | Portable? |
|----------|---------|-----------|
| `AKBP.md` | Human-readable entry point with starter memory rules, review policy, and layout notes | Yes |
| `akbp.json` | Machine-readable Knowledge Base Card for tooling | Yes |
| `raw/sources/sources.jsonl` | Registered evidence with locator, hash, and metadata | Yes |
| `claims/claims.jsonl` | Reviewed durable claims with type, status, confidence, and evidence | Yes |
| `graph/relations.jsonl` | Lifecycle and semantic links such as supersession | Yes |
| `.akbp/` | Rebuildable runtime state such as local indexes | No |
| export bundle | Portable manifest plus artifacts for inspection or import | Yes |

The trust boundary is just as important as the layout:

| Moment | Expected behavior |
|--------|-------------------|
| Agent proposes memory | Use `dry_run:true` and show the preview |
| Agent skips approval | Return `approval_required` without durable writes |
| User or trusted local policy approves | Repeat the same request with `approved:true` |
| Later agent needs context | Use `akbp.context` or `akbp.session.start` and show citations |
| Knowledge changes | Supersede or contradict old claims instead of deleting history |

If a tool hides these artifacts or applies writes without the preview/approval step, it is bypassing the main AKBP value.
The generated `AKBP.md` now makes that policy visible on first run, so adapters and humans have a shared local rule sheet before any memory is written.
If a project needs a stricter starter policy, copy or merge `templates/project-memory-rules/AKBP.md` and use `docs/TEMPLATES.md` as the setup guide.

## Choose the knowledge-base scope first

Recent agent-memory tools often start with a server, profile, or sidecar watcher.
AKBP should start with a simpler question: which durable knowledge base should
future agents trust?

| Scope | Use when | Safe default | Avoid |
|-------|----------|--------------|-------|
| Repo-local KB | A coding agent needs project decisions, release rules, incidents, or architecture context for one repository | Keep `AKBP.md`, `akbp.json`, claims, sources, and graph records in or beside the repo, then retrieve context at session start | Mixing unrelated personal memory or private chat exports into the project KB |
| Team-shared KB | Multiple people or agents need the same reviewed project knowledge | Store only approved team knowledge with citations, run verification in CI, and export bundles for review | Treating one person's unreviewed local notes as team truth |
| Personal assistant KB | A local assistant needs user preferences or recurring workflow context across projects | Keep it outside public repos, use read-only adapters first, and require review before durable writes | Committing personal preferences, DMs, credentials, or private logs into a public project |
| Transcript sidecar KB | A watcher or hook summarizes agent session transcripts after work finishes | Preview `akbp.session.end` or `akbp.crystallize_session` with `dry_run:true`, then apply only reviewed claims | Automatically converting every transcript line into durable memory |
| Migration KB | Existing notes or memory exports need cleanup before reuse | Run `import-check` and dry-run `import-apply`, reject uncited or unsafe records, then approve only the clean subset | Bulk-loading stale, uncited, or secret-bearing memory because it is available |

The default recommendation is one repo-local KB per active project. Add a
team-shared or personal KB only when the trust boundary is explicit and the
adapter knows which KB it is reading from.

## Fast path

From a clean checkout:

```bash
git clone https://github.com/rohitg00/akbp.git
cd akbp
make demo
```

The demo creates a temporary knowledge base, adds evidence, writes a reviewed decision, verifies sources, builds search, retrieves context, supersedes stale knowledge, exports a bundle, checks the bundle, and runs level 3 conformance.
The first write goes through the JSONL tool-server flow: capability discovery, dry-run preview, unapproved write rejection, approved apply, and approved index refresh.
For adapter installers and setup UIs, `akbp discover` and `akbp client-config`
also emit `ten_minute_proof`: a machine-readable checklist that proves AKBP is
local-first, needs no Docker, cloud account, or secrets, retrieves cited
startup context, blocks unapproved writes, and exports a checked portable
bundle.
They also emit `inherited_repo_intake`, a machine-readable takeover checklist
for repositories with older agent-written changes, handoff notes, or memory
exports: resolve the KB, stay read-only, verify sources, and require cited
warning-free context before planning from inherited memory.

Expected success markers:

```text
AKBP quickstart demo
"id": "caps", "ok": true
"id": "ingest-preview"
"code": "approval_required"
"id": "ingest-approved"
"id": "index-approved"
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
python3 cli/akbp.py --path "$TMP_KB" init --level 0
printf '%s\n' "Release work should stay small, reviewed, and evidence-backed." > "$TMP_KB/session-note.md"
python3 cli/akbp.py --path "$TMP_KB" source add "$TMP_KB/session-note.md" --type file --title "Session note"
python3 cli/akbp.py --path "$TMP_KB" ingest "$TMP_KB/session-note.md" --claim "Release work should stay small, reviewed, and evidence-backed." --claim-type decision
python3 cli/akbp.py --path "$TMP_KB" source verify --fail-on-issue
python3 cli/akbp.py --path "$TMP_KB" index --incremental
python3 cli/akbp.py --path "$TMP_KB" doctor
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

`akbp status` is the quick dashboard health check for a knowledge base. It keeps the old object counts, and also returns dashboard-ready sections for the trust boundary, default scope, latest claims, claim type/status counts, source verification health, audit count, index presence, highest passing conformance level, and adapter readiness. For installer or startup checks, pass `--profile startup-context`, `--profile read-only`, or `--profile reviewed-writes` to include `requested_profile_ready` without loading the full doctor report.

`akbp doctor` is the adoption check. It returns pass/fail checks, warnings, and concrete next steps so a new user or adapter author can see whether the knowledge base is ready for retrieval and approved writes.
Its `workflow` section maps the same result onto the first-run path: create the knowledge base, register evidence, create a reviewed claim, build retrieval, pass adapter checks, and export a portable bundle.

## Agent write-safety path

Use the JSONL tool server to see how an adapter should behave.

```bash
TMP_KB="$(mktemp -d)/akbp-tool-first-run"
python3 cli/akbp.py --path "$TMP_KB" init --level 0

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
- Adoption reviewer: run `examples/adoption-preflight/run.sh` to verify the first-run trust boundary before connecting an adapter or host.
- Choosing an architecture: read `docs/ADOPTION_DECISION_GUIDE.md` before deciding whether AKBP should sit beside an existing memory server, local index, or agent adapter.
- Adapter author: read `docs/ADAPTER_AUTHOR_QUICKSTART.md`, then inspect `examples/adapter-lifecycle/`.
- Adapter quality reviewer: run `examples/structured-output-harness/run.sh` before trusting recalled context or enabling reviewed writes.
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
