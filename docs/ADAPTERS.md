# AKBP Adapter Plan

## Adapter purpose

Adapters make AKBP usable from specific agent runtimes without changing the protocol.

## Reference template

A generic coding-agent adapter template is available at:

```text
adapters/coding-agent-template/
```

Use this template before creating runtime-specific adapters. It defines startup context retrieval, safe writes, session crystallization, and privacy defaults without adding a new memory format.

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

Integration style:

- `CLAUDE.md` instruction block
- tool-server implementation config
- optional shell command for session crystallization

## Codex

Integration style:

- `repository instruction files` instruction block
- tool protocol or CLI command usage
- session-summary crystallization pattern

## Cursor

Integration style:

- Cursor rules
- tool protocol config where supported
- project-local `.akbp/` discovery

## OpenClaw

Integration style:

- workspace instructions
- memory flush bridge
- task/session crystallization
- tool protocol/CLI calls through first-class tools where possible

## Gemini CLI

Integration style:

- agent instruction file
- CLI/tool protocol calls
- local workspace discovery

## Adapter rule

Adapters must not invent their own memory format. They can add runtime-specific instructions, but durable artifacts must remain AKBP-compatible.
