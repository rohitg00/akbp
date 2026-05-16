# Context compaction recovery

This example shows the AKBP recovery path after an agent loses chat context or resumes from a compacted handoff.

The flow records an old relative-date handoff, supersedes it with a cited handoff snapshot that uses absolute dates and review-gated next actions, then verifies that `akbp.session.start` retrieves the current cited claim inside a small context budget.

Adapters that have a pre-compaction or session-summary hook should run the same
review boundary before context is pruned: call `akbp.session.end` with
`dry_run:true`, inspect the proposed durable candidates, and only apply the exact
reviewed request with `approved:true`. If the preview cannot preserve citations,
absolute dates, lifecycle state, and the source ids needed for later recall, the
adapter should keep the summary transient and continue without writing AKBP
memory.

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
- pre-compaction hooks should preview `akbp.session.end` instead of silently saving raw chat
