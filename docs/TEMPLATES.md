# AKBP templates

Templates are starter artifacts for teams that want AKBP's memory rules visible before agents write durable knowledge.

Use them when a new repository needs a small, reviewable setup path and the full adapter template would be too much ceremony.

## Project memory rules

Path:

```text
templates/project-memory-rules/AKBP.md
```

Copy this file to the root of a project knowledge base or merge its sections into an existing `AKBP.md`.

It defines:

- what counts as durable project knowledge
- which evidence is acceptable
- when agents must use `dry_run:true`
- who or what can approve writes
- what must never be stored
- when to supersede or contradict stale knowledge
- which validation commands should pass before sharing memory

The template is intentionally local-first and tool-neutral. It does not add a new runtime store. It tells agents how to treat AKBP files as the durable source of truth.

## Recommended first use

1. Initialize a knowledge base with `akbp init`.
2. Replace the generated `AKBP.md` with the project memory rules template, or copy the relevant sections into it.
3. Edit the approval policy for the project.
4. Add one real source with `akbp source add`.
5. Preview the first durable claim with `dry_run:true`.
6. Apply only after the preview is reviewed and request-level `approved:true` is present.
7. Run `akbp doctor` before wiring an adapter.

## Why this exists

Recent agent-memory and agent-workflow products are easiest to adopt when they start from a concrete rule file or harness, not a long integration guide. AKBP should give the same first artifact while keeping the protocol boundary clear: reviewed claims, cited sources, audit events, lifecycle relations, and portable exports remain the product.

The template makes the review boundary explicit before any runtime-specific adapter is involved.
