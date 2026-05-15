# JSONL quickstart example

This example gives adapter authors one runnable JSONL sequence for the normal AKBP tool-server path.

Run it from the repository root:

```bash
./examples/jsonl-quickstart/run.sh
```

To inspect the exact adapter transcript, capture the generated request and
response JSONL files:

```bash
AKBP_JSONL_QUICKSTART_TRACE_DIR=/tmp/akbp-jsonl-trace ./examples/jsonl-quickstart/run.sh
sed -n '1,120p' /tmp/akbp-jsonl-trace/requests.jsonl
sed -n '1,120p' /tmp/akbp-jsonl-trace/responses.jsonl
```

The trace is useful when wiring a new host because it shows the concrete
envelope shape, `dry_run:true` preview, `approval_required` stop, `approved:true`
apply, index refresh, cited recall, and portable export in the order an adapter
should preserve.

Expected success markers:

```text
AKBP JSONL quickstart example
capability discovery ok
session start cited context ok
dry-run write preview ok
unapproved write blocked ok
approved write apply ok
index refresh ok
cited recall ok
portable export ok
AKBP JSONL quickstart example passed
```

## Flow covered

The script verifies the sequence a new adapter should implement before exposing write-capable memory:

1. Call `akbp.capabilities` and require schema-backed JSONL responses.
2. Call `akbp.session.start` before planning and require cited context when existing claims are present.
3. Preview a proposed durable claim with `dry_run:true`.
4. Treat an unapproved non-dry-run write as a hard `approval_required` stop.
5. Repeat the same write with `approved:true` only after review.
6. Refresh retrieval with approved `akbp.index`.
7. Call `akbp.context` again and check the approved claim is recallable.
8. Call `akbp.export` and verify the portable bundle excludes local indexes.

This is the shortest adapter contract AKBP needs to make visible: retrieve before planning, preview before writing, require approval before durable memory, then recall cited context and export portable artifacts.
