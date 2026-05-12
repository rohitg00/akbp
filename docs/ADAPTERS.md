# AKBP Adapter Plan

## Adapter purpose

Adapters make AKBP usable from specific agent runtimes without changing the protocol.

## Reference template

A generic coding-agent adapter template is available at:

```text
adapters/coding-agent-template/
```

A complete runtime-neutral example adapter is available at:

```text
adapters/example-coding-agent/
```

A generic git-native agent adapter template is available at:

```text
adapters/git-native-agent/
```

Use it for agents that keep runtime state, instructions, or skills in a repository and need AKBP as the durable knowledge layer rather than another private memory folder.

A public-safe OpenClaw workspace adapter is available at:

```text
adapters/openclaw/
```

Use `docs/ADAPTER_AUTHOR_QUICKSTART.md` before creating runtime-specific adapters. Use the template before creating runtime-specific adapters. Use the example to confirm the minimum complete file shape. Both define startup context retrieval, safe writes, session crystallization, and privacy defaults without adding a new memory format.

## Required adapter files

Each adapter should include:

```text
README.md
instructions.md
config.example.json
session-start.md
session-end.md
privacy.md
```

## Claude Code

Reference adapter:

```text
adapters/claude-code/
```

Integration style:

- `CLAUDE.md` instruction block
- tool-server implementation config
- optional shell command for session crystallization

## Codex

Reference adapter:

```text
adapters/codex/
```

Integration style:

- `repository instruction files` instruction block
- tool protocol or CLI command usage
- session-summary crystallization pattern

## Cursor

Reference adapter:

```text
adapters/cursor/
```

Integration style:

- Cursor rules
- tool protocol config where supported
- project-local `.akbp/` discovery

## OpenClaw

Reference adapter:

```text
adapters/openclaw/
```

Integration style:

- workspace instructions
- memory flush bridge
- task/session crystallization
- tool protocol/CLI calls through first-class tools where possible

## Gemini CLI

Reference adapter:

```text
adapters/gemini-cli/
```

Integration style:

- agent instruction file
- CLI/tool protocol calls
- local workspace discovery

## Contributing an adapter

Use this checklist before opening a pull request:

- Read `docs/ADAPTER_AUTHOR_QUICKSTART.md`.
- Start from `adapters/coding-agent-template/` unless the target environment is not a coding agent.
- Keep runtime-specific setup in adapter docs, not in the protocol spec.
- Point the startup and shutdown loop to `docs/AGENT_FLOW.md`.
- Use public-safe runtime names and avoid private workspace paths, tokens, screenshots, cookies, logs, or user-specific config.
- Include `README.md`, `instructions.md`, `config.example.json`, `session-start.md`, `session-end.md`, and `privacy.md` when the runtime supports those concepts.
- In `config.example.json`, include an explicit `akbp.lifecycle` mapping for `akbp.session.start` and `akbp.session.end`, with shutdown apply mode requiring approval.
- Show both read flow and write flow: retrieve context first, write cited durable records after work, then validate or index when useful.
- Prefer `dry_run` examples for write-capable tool-server calls.
- Treat `review_required` and `apply_instruction` as UI/runtime obligations, not optional metadata.
- Prefer `akbp.session.end` for transcript-backed session-end memory, with dry-run preview before apply.
- Keep durable output in AKBP artifacts: markdown wiki pages, JSONL claims, JSONL graph records, sources, audit events, and context packs.
- Do not introduce a new memory format or runtime-only storage as the source of truth.
- Run `make validate` before submitting.

## Adapter rule

Adapters must not invent their own memory format. They can add runtime-specific instructions, but durable artifacts must remain AKBP-compatible.
