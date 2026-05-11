# Multi-agent consistency demo

This demo shows why AKBP is more than generic persistent memory.

Two simulated agents operate on the same local knowledge base:

1. Agent A records a durable release decision with evidence.
2. Agent B retrieves the prior decision before acting.
3. Agent B supersedes the old decision with a more precise, validation-backed decision.
4. AKBP keeps both claims and the lifecycle relation instead of silently overwriting history.

## Run it

From the repository root:

```bash
examples/multi-agent-consistency-demo/run.sh
```

Expected success marker:

```text
AKBP multi-agent consistency demo passed
```

## What to notice

- Agent B does not start from an empty transcript.
- Retrieved context includes the earlier durable claim.
- The new claim supersedes the old one without deleting it.
- Conformance level 3 verifies lifecycle relations are present.

## Why this matters

AKBP is a portable consistency layer for project knowledge. It lets multiple runtimes share reviewed claims, cited evidence, and lifecycle updates without depending on one chat history or one hosted memory product.
