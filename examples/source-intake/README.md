# Source intake playbook

Use this flow when an agent needs to turn files, transcripts, exports, or notes into durable AKBP knowledge.

Run the executable example from the repository root:

```bash
./examples/source-intake/run.sh
```

The example covers the first inherited-repo intake loop: record file evidence, preview an ingest, reject the unapproved write, apply only with approval, rebuild the index, retrieve cited startup context, and reject an unsafe import.

## Rules

1. Record source material before making durable claims.
2. Keep source records small enough to review.
3. Use hashes for local file evidence when possible.
4. Run dry-run imports before durable writes.
5. Treat secret-like values as rejection signals, not content to preserve.
6. Keep claim evidence ids connected to real source records.
7. Rebuild search indexes only after accepted writes.

## Local file evidence

```bash
akbp --path ./kb source add notes/release-review.md --type file --title "Release review notes"
akbp --path ./kb remember "Release review requires a rollback checklist." --evidence source_...
```

For file sources, AKBP stores a SHA-256 hash when the file can be read. Agents should prefer relative paths inside the reviewed workspace.

## Transcript evidence

```bash
akbp --path ./kb crystallize session.md --dry-run
akbp --path ./kb crystallize session.md --apply
```

Use dry run first. Apply only when the summary, decisions, blockers, preferences, and action candidates are safe to store.

## JSONL exchange evidence

```bash
akbp --path ./kb import-check incoming.jsonl --fail-on-rejected
akbp --path ./kb import-apply incoming.jsonl --dry-run
akbp --path ./kb import-apply incoming.jsonl --approved
```

Reject the intake when:

- a line is invalid JSON
- an object has a secret-like value
- a claim cites an unknown `source_...` evidence id
- `review.ready_for_reviewed_apply` is false because a claim is uncited or only points at non-source evidence
- the dry run shows writes that do not match the reviewed plan

## Review checklist

Before accepting durable writes, confirm:

- source ids are stable and descriptive enough for later citation
- claims are atomic and not broad summaries
- evidence ids point to recorded source rows
- redaction happened before writes
- planned writes match the user-approved task
- duplicate imports are skipped instead of rewritten

Expected success markers:

```text
AKBP source intake example
review-gated source intake ok
cited intake context ok
AKBP source intake example passed
```
