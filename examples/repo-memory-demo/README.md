# Repo memory demo

This example shows how AKBP can turn a repository work session into durable, cited project memory.

The demo uses local fixture files instead of a live hosted repo so it is safe, repeatable, and CI-friendly.

## Story

An agent reads three project artifacts:

- an issue report
- a pull request summary
- a release note

AKBP captures durable project knowledge from those artifacts, indexes it, and retrieves context for a later agent session.

## Run

From the repository root:

```bash
examples/repo-memory-demo/run.sh
```

Expected success marker:

```text
AKBP repo memory demo passed
```

## Why this matters

This is the real-world use case people understand quickly:

> Do not make the next agent reread every issue, PR, and release note. Store reviewed project knowledge once, cite it, and retrieve it later.
