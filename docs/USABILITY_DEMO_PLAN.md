# Usability demo plan

Use this page to show AKBP as a practical tool users can run today while the implementation is still alpha.

## One-sentence story

AKBP gives local agents a reviewed, cited project memory that survives across sessions without trusting opaque chat history or silent writes.

## Best public demo

The strongest public demo is a 6 minute terminal walkthrough that starts with an empty directory and ends with a reusable knowledge base:

1. Initialize a knowledge base.
2. Register a source note as evidence.
3. Preview a durable claim before writing it.
4. Apply the reviewed write.
5. Build the search index.
6. Retrieve cited context for the next agent session.
7. Export and check a portable bundle.
8. Show level 3 conformance.

Run the shipped happy path first:

```bash
git clone https://github.com/rohitg00/akbp.git
cd akbp
make demo
```

Then show one manual write-safety moment with the JSONL tool server:

```bash
TMP_KB="$(mktemp -d)/akbp-demo-kb"
python3 cli/akbp.py --path "$TMP_KB" init

printf '%s\n' \
  '{"id":"preview","method":"akbp.remember","path":"'"$TMP_KB"'","dry_run":true,"params":{"text":"Release work should name a rollback owner before the deployment window starts.","type":"workflow"}}' \
  '{"id":"blocked","method":"akbp.remember","path":"'"$TMP_KB"'","params":{"text":"Unreviewed durable writes should be rejected.","type":"policy"}}' \
  | python3 tool-server/akbp_tool_server.py
```

Expected public-safe point to highlight:

- `preview` returns `ok:true`, `review_required:true`, and `apply_instruction`.
- `blocked` returns `ok:false` with `error.code:"approval_required"`.
- The agent can propose memory, but durable writes require review.

## Talk track

### Hook

Most agent workflows lose their useful context at session boundaries. AKBP makes the handoff explicit: facts, decisions, workflows, sources, hashes, lifecycle relations, and audit history are stored as local files.

### What the user sees

The user sees normal files:

```text
AKBP.md
akbp.json
claims/claims.jsonl
raw/sources/sources.jsonl
graph/relations.jsonl
wiki/
.akbp/audit.log.jsonl
```

The agent sees a stable interface:

```json
{"id":"ctx","method":"akbp.context","path":".","params":{"task":"prepare release","limit":5}}
```

### The key usability claim

AKBP is useful because the operator can inspect and version the memory layer. It is not a magic memory box. It is a small, local, review-gated contract that coding agents, editors, task runners, and local assistants can share.

### Safety line

Write-capable calls start as dry-run previews. Non-dry-run writes require request-level approval. Import and export checks reject or flag unsafe bundles before durable writes.

## Demo assets to prepare

### Required

- Terminal recording of `make demo` from a clean checkout.
- A short clip showing the JSONL dry-run plus `approval_required` rejection.
- A screenshot of `claims/claims.jsonl` and `raw/sources/sources.jsonl` after the demo.
- A screenshot of `akbp context "prepare the next public alpha release"` returning cited items.
- A copy-paste README block linking to `docs/ADAPTER_AUTHOR_QUICKSTART.md`, `docs/TOOL_CONTRACT.md`, and `docs/SECURITY_MODEL.md`.

### Optional

- 60 second product clip: empty repo to cited context.
- 3 minute adapter clip: `akbp.capabilities`, `akbp.session.start`, `akbp.session.end` dry-run, approved apply.
- 10 minute maintainer clip: export, export-check, import-check, import-apply dry-run, conformance.

## Public launch sequence

1. Publish the short terminal demo first. Keep the claim narrow: public alpha, local-first, review-gated durable agent knowledge.
2. Follow with an adapter-author post aimed at tool builders.
3. Follow with a safety post explaining dry-run, approval, source hashes, redaction, import/export checks, and conformance.
4. Ask early users for failure cases that can become fixtures under `benchmarks/fixtures/`.
5. Turn every credible usability complaint into one of: README change, example, test, benchmark fixture, or adapter checklist item.

## What not to claim

Do not claim AKBP is production-ready, hosted memory, a vector database, a chat-history replacement, or a complete agent runtime. Public copy should say alpha and tie every claim to shipped files, schemas, examples, fixtures, and validation commands.

## Success criteria

A public viewer should understand these five things within 6 minutes:

1. How to run AKBP locally.
2. Where the durable knowledge is stored.
3. How a claim cites evidence.
4. Why write review matters.
5. How another agent session retrieves cited context later.
