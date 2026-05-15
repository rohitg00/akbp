# Portable bundle review flow

This example shows how an agent should move AKBP knowledge between environments without trusting opaque state.

## Run

From the repository root:

```bash
examples/portable-bundle/run.sh
```

Expected success marker:

```text
AKBP portable bundle example passed
```

## Producer

```bash
akbp --path ./kb export --output bundle.json
```

The exported JSON includes:

- `card`: the knowledge base card
- `claims`: durable claims
- `sources`: cited source records
- `entities`: graph entities
- `relations`: graph relations
- `manifest`: counts, artifact paths, hashes, safety flags, and verification metadata

Local indexes and engine-owned files are intentionally excluded.

## Reviewer

Before accepting a bundle, inspect the manifest and object counts.

Minimum review checklist:

1. Confirm `manifest.format` is `akbp-portable-bundle`.
2. Confirm `manifest.counts` matches the arrays in the bundle.
3. Confirm `manifest.safety.excludes_local_state` is true.
4. Confirm `manifest.safety.excludes_indexes` is true.
5. Confirm the bundle does not contain secret-like values.
6. Confirm claims cite evidence that is present in the target knowledge base or included in the incoming source records.

## Consumer

For line-oriented imports, review before write:

```bash
akbp --path ./target-kb import-check incoming.jsonl --fail-on-rejected
akbp --path ./target-kb import-apply incoming.jsonl --dry-run
akbp --path ./target-kb import-apply incoming.jsonl --approved
```

The dry run is the contract boundary. Agents should not apply durable writes until the accepted ids, rejected ids, planned write ids, and skipped-existing ids have been reviewed by the runtime or user policy.

After approval, rebuild retrieval state and query the target knowledge base:

```bash
akbp --path ./target-kb index --incremental
akbp --path ./target-kb context "continue the handoff"
```

The target should recall only reviewed portable claims. Local indexes, caches, and engine-owned files are intentionally excluded from the producer bundle and rebuilt by the consumer.
