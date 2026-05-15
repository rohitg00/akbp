# Read-only adapter

This example shows how an adapter can integrate AKBP before it has a reviewed write UI.

The adapter discovers `akbp.capabilities`, uses `result.profiles.read_only` as its allowlist, retrieves cited context, and rejects write-capable methods locally instead of accidentally creating durable memory.

## Run

From the repository root:

```bash
examples/read-only-adapter/run.sh
```

Expected success marker:

```text
AKBP read-only adapter example passed
```

## What it proves

- adapters can start with retrieval and validation only
- `result.profiles.read_only` contains methods that do not mutate the knowledge base
- write-capable methods stay blocked until the adapter has review UX for `dry_run`, `review_required`, `apply_instruction`, and `approved:true`

