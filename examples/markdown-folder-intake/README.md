# Markdown folder intake

Use this flow when a team already has useful agent notes, ADR drafts, or debugging writeups scattered across a repository and wants to promote only reviewed knowledge into AKBP.

Run the executable example from the repository root:

```bash
./examples/markdown-folder-intake/run.sh
```

The example creates a small markdown note folder, registers each file as source evidence, previews the durable claims, proves unapproved writes are blocked, applies only reviewed claims, rebuilds the index, and retrieves cited startup context.

## Promotion rules

1. Treat the existing markdown folder as evidence, not trusted durable memory.
2. Register every note as a source before creating a claim from it.
3. Keep each promoted claim atomic enough to review.
4. Preview writes through the JSONL server before applying them.
5. Apply only after the note, source id, claim text, and claim type match the reviewed plan.
6. Retrieve context with citations before letting a later agent plan from it.

This pattern covers the common migration gap where agents produce useful local markdown, but teams still need review, citation, lifecycle, export, and adapter-safe retrieval before that knowledge should influence later coding sessions.

Expected success markers:

```text
AKBP markdown folder intake example
registered markdown sources ok
review-gated markdown promotion ok
cited markdown context ok
AKBP markdown folder intake example passed
```
