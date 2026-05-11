# AKBP Bench example

This is a small, runnable benchmark-style example for showing AKBP's real value to users.

It checks whether a knowledge base can support the core public-alpha promises:

1. record cited project knowledge
2. retrieve that knowledge in a later session
3. preserve superseded decisions instead of overwriting them
4. export a portable bundle
5. pass conformance checks

This is not a leaderboard yet. It is a clear baseline that can grow into real-world benchmark fixtures.

## Run

From the repository root:

```bash
examples/akbp-bench/run.sh
```

Expected success marker:

```text
AKBP bench example passed
```

The script prints a compact scorecard so users can see what passed and why.

## What this demonstrates

AKBP is useful when memory quality needs measurable properties:

- evidence-backed claims
- later retrieval with citations
- lifecycle updates
- portable export bundles
- conformance levels

A generic memory note is not enough. The benchmark checks the behavior that makes project knowledge reusable across tools.
