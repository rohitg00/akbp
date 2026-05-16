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
nested discovery profile proof ok
CLI startup context quality gate ok
cited startup context becomes ready ok
capability negotiation read-only profile ok
unapproved write rejection ok
portable client config hides local paths ok
response contract approval stop action ok
local-first adoption probe contract ok
AKBP adoption preflight example passed
```

## Flow covered

The script verifies the minimum safe adoption path before an adapter or host
treats AKBP as durable memory:

1. Initialize a local knowledge base and run `akbp doctor`.
2. Run `akbp discover` from a nested workspace and confirm it resolves the
   knowledge-base root, profile selection, adapter prompt contract,
   recommended harness, and ten-minute proof.
3. Confirm an empty first run has no blocking errors but is not write-ready.
4. Add cited evidence, a reviewed claim, and an index.
5. Run the CLI context quality gate with `--min-items 1 --require-citations`.
6. Confirm startup context is ready and returns citations.
7. Confirm capability negotiation satisfies the read-only profile and exposes
   structured `approval_required` errors.
8. Generate a portable read-only client config that uses `<AKBP_KB_PATH>`
   instead of committing a local absolute path.
9. Prove the generated response contract tells adapters to branch on
   `error.code` and stop the write path on `approval_required`.
10. Prove the generated local-first adoption probe gives installer UIs a
    runnable comparison check before positioning AKBP against memory servers.
11. Prove `akbp.remember` rejects unapproved durable writes.

This makes the current product promise concrete: AKBP can sit beside a memory
server or tool-protocol host, but the trusted state remains local, cited, reviewable, and portable.
