# Quickstart demo

This is the copy-paste AKBP happy path. It creates a fresh knowledge base, discovers tool-server capabilities, previews one durable decision, rejects the same write without approval, applies the reviewed write, verifies evidence, builds the local search index, retrieves context, supersedes stale knowledge, exports a portable bundle, checks the bundle, and runs conformance.

Run it from the repo root:

```bash
make demo
```

Or run the script directly:

```bash
./examples/quickstart-demo/run.sh
```

Or choose the output knowledge-base directory:

```bash
./examples/quickstart-demo/run.sh /tmp/akbp-demo-kb
```

Expected success markers:

```text
AKBP quickstart demo
Initialized AKBP knowledge base at ...
{"id": "caps", "ok": true}
{"dry_run": true, "id": "ingest-preview"
{"error": {"code": "approval_required"}, "id": "ingest-blocked", "ok": false}
{"id": "ingest-approved", "ok": true
{"id": "index-approved", "indexed":
"verified": 1
"results": [
"context": [
"supersedes": [
"event": "supersede"
"ok": true
AKBP quickstart demo passed
```

What this proves:

1. The CLI can create an AKBP layout from scratch.
2. The JSONL tool server advertises capability negotiation and write policy.
3. Source material and a durable decision can be previewed before writing.
4. The same write is rejected until the request carries explicit approval.
5. Approved knowledge can be indexed, searched, and returned in a context pack.
6. A newer decision can supersede stale knowledge without deleting audit history.
7. Export bundles include a manifest and can be checked before sharing.
8. The generated knowledge base passes level 3 conformance.

If this fails, see `docs/TROUBLESHOOTING.md`.
