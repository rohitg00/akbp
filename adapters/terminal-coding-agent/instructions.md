# Terminal Coding Agent AKBP Instructions

Use AKBP as the project-local durable knowledge layer when working from a terminal coding environment.

## Startup

1. Discover `akbp.json` from the current directory or parent directories.
2. Prefer the JSONL local tool server when available.
3. Call `akbp.capabilities` before assuming write or search methods exist.
4. Fetch task-specific context before planning multi-step or multi-file work.

## During work

- Cite retrieved claims when they influence implementation decisions.
- Keep command output, stack traces, and logs out of durable memory unless they explain a durable decision.
- Use `dry_run` for proposed writes unless durable memory writes are already approved.
- Refresh the search index after meaningful writes when the runtime does not do it automatically.

## Shutdown

- Crystallize durable decisions, workflows, blockers, preferences, and follow-ups.
- Supersede stale claims instead of deleting history.
- Follow `docs/AGENT_FLOW.md` for the full loop.
