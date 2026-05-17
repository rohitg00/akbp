# Project understanding bridge

Use this flow when a project already has a useful `project-understanding.md`
or similar agent scratchpad and the team needs to decide whether it should stay
plain markdown or become reviewed AKBP knowledge.

Run the executable example from the repository root:

```bash
./examples/project-understanding-bridge/run.sh
```

The example treats the markdown file as source evidence, previews the durable
claims that would be promoted, proves an unapproved write is blocked, applies
only reviewed claims, retrieves cited startup context, and export-checks the
portable bundle.

## Decision rule

Keep the markdown file as scratchpad context when one runtime owns the work and
history does not need citations or lifecycle state. Promote selected claims into
AKBP when future agents must plan from cited, reviewed, export-checkable project
knowledge.

Expected success markers:

```text
AKBP project understanding bridge example
plain markdown comparison contract ok
review-gated promotion from markdown ok
plain markdown registered as evidence ok
cited startup context from promoted markdown ok
portable bridge export-check ok
AKBP project understanding bridge example passed
```
