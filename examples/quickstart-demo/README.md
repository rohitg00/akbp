# Quickstart demo

This is the copy-paste AKBP happy path. It creates a fresh knowledge base, records a source, imports one durable decision, verifies evidence, builds the local search index, retrieves context, exports a portable bundle, checks the bundle, and runs conformance.

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
"verified": 1
"results": [
"context": [
"ok": true
AKBP quickstart demo passed
```

What this proves:

1. The CLI can create an AKBP layout from scratch.
2. Source material is registered and hash-verified before durable use.
3. A durable decision can be ingested, indexed, searched, and returned in a context pack.
4. Export bundles include a manifest and can be checked before sharing.
5. The generated knowledge base passes level 3 conformance.

If this fails, see `docs/TROUBLESHOOTING.md`.
