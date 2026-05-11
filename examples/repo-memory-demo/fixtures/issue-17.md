# Issue 17: imports need safer review

Users want to import JSONL memory bundles from other tools, but unsafe records must not be applied directly.

Acceptance criteria:

- validate the bundle before apply
- reject unknown evidence ids
- require explicit approval for durable writes
