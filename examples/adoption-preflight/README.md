# AKBP adoption preflight example

This example is a short first-run gate for users comparing AKBP with local
memory servers or tool-protocol memory tools.

Run it from the repository root:

```bash
./examples/adoption-preflight/run.sh
```

Expected success markers:

```text
AKBP adoption preflight example
fresh KB starts with read-only trust boundary ok
CLI startup context quality gate ok
cited startup context becomes ready ok
unapproved write rejection ok
portable client config hides local paths ok
AKBP adoption preflight example passed
```

## Flow covered

The script verifies the minimum safe adoption path before an adapter or host
treats AKBP as durable memory:

1. Initialize a local knowledge base and run `akbp doctor`.
2. Confirm an empty first run has no blocking errors but is not write-ready.
3. Add cited evidence, a reviewed claim, and an index.
4. Run the CLI context quality gate with `--min-items 1 --require-citations`.
5. Confirm startup context is ready and returns citations.
6. Generate a portable read-only client config that uses `<AKBP_KB_PATH>`
   instead of committing a local absolute path.
7. Prove `akbp.remember` rejects unapproved durable writes.

This makes the current product promise concrete: AKBP can sit beside a memory
server or tool-protocol host, but the trusted state remains local, cited, reviewable, and portable.
