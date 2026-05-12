# Git-native agent handoff example

This example shows how a repo-backed coding agent can use AKBP as a small, auditable handoff layer.

The point is not to replace Git. Git tracks code. AKBP tracks reviewed project knowledge that the next agent should retrieve before planning work.

## Flow

1. Seed a temporary knowledge base with reviewed adapter policy.
2. Start a new agent session with `akbp.session.start`.
3. Verify the returned context includes cited handoff claims.
4. Preview shutdown memory with `akbp.session.end` and `dry_run:true`.
5. Apply only after review with `approved:true`.
6. Refresh search with `akbp.index`.

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
- Use `akbp.session.end` with request-level `dry_run:true` before shutdown writes.
- Require explicit review before repeating the same request with `approved:true`.
- Run `akbp.index` after approved writes when the adapter needs fresh local search.
