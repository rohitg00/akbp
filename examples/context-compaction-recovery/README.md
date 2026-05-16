# Context compaction recovery

This example shows the AKBP recovery path after an agent loses chat context or resumes from a compacted handoff.

The flow records an old relative-date handoff, supersedes it with a cited handoff snapshot that uses absolute dates and review-gated next actions, then verifies that `akbp.session.start` retrieves the current cited claim inside a small context budget.

## Run

From the repository root:

```bash
examples/context-compaction-recovery/run.sh
```

Expected success marker:

```text
AKBP context compaction recovery example passed
```

## What it proves

- agents can recover from compaction by asking AKBP for bounded startup context
- cited, current handoff claims outrank stale relative-date memory
- lifecycle state is preserved instead of overwriting the old handoff
- adapters can assert citations, budget metadata, and the current claim before planning
