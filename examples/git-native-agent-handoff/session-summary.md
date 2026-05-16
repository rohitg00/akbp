# Git-native agent session summary

## Task

Continue repository adapter work safely after reading durable project context.

## Decisions

- Use `akbp.session.start` before planning substantial repository work.
- Treat retrieved citations as handoff context, not hidden prompt state.
- Preserve branch name, commit SHA or dirty-worktree marker, and source ids before reusing branch-scoped handoff memory.
- Use `akbp.cite` to explain the evidence behind a branch-scoped claim before promotion or reuse.
- Use `akbp.session.end` to preview durable shutdown memory with `dry_run:true`.
- Apply shutdown memory only after review with `approved:true`.

## Validation

- Ran local tests before proposing durable memory.
- Indexed the knowledge base after approved writes.

## Blockers

- None.
