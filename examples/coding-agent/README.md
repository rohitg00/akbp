# Coding Agent Example

Use AKBP to preserve project knowledge across agent sessions.

Example durable claims:

- This project uses Bun instead of npm.
- Production deploys require manual approval.
- The auth migration decision superseded the old session-cookie design.
- Do not edit generated files under `dist/`.

Example session crystallization:

```text
Claude Code fixes a bug
→ AKBP stores changed files, root cause, test command, and decision
→ Codex starts later and retrieves the fix context automatically
```
