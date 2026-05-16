# Git-native agent handoff example

This example shows how a repo-backed coding agent can use AKBP as a small, auditable handoff layer.

The point is not to replace Git. Git tracks code. AKBP tracks reviewed project knowledge that the next agent should retrieve before planning work.

## Flow

1. Seed a temporary knowledge base with reviewed adapter policy.
2. Record a branch-scoped handoff claim with the branch name, commit or dirty marker, and cited source ids.
3. Start a new agent session with `akbp.session.start`.
4. Verify the returned context includes cited handoff claims.
5. Explain the branch-scoped handoff with `akbp.cite` before reusing it.
6. Preview shutdown memory with `akbp.session.end` and `dry_run:true`.
7. Apply only after review with `approved:true`.
8. Refresh search with `akbp.index`.

## Run

From the repository root:

```bash
examples/git-native-agent-handoff/run.sh
```

Expected success marker:

```text
AKBP git-native handoff example passed
```

## Adapter contract shown

- Call `akbp.capabilities` before using lifecycle methods.
- Use `akbp.session.start` to retrieve cited context before planning.
- Keep repository state in Git. Keep durable agent memory in AKBP.
- Preserve branch name, commit SHA or dirty-worktree marker, and source ids in reviewed handoff claims.
- Use `akbp.cite` when an adapter needs to explain why branch-scoped memory is safe to reuse.
- Use `akbp.session.end` with request-level `dry_run:true` before shutdown writes.
- Require explicit review before repeating the same request with `approved:true`.
- Run `akbp.index` after approved writes when the adapter needs fresh local search.
