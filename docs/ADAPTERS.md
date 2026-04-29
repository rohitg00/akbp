# AKBP Adapter Plan

## Adapter purpose

Adapters make AKBP usable from specific agent runtimes without changing the protocol.

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
- MCP server config
- optional shell command for session crystallization

## Codex

Integration style:

- `AGENTS.md` instruction block
- MCP or CLI command usage
- session-summary crystallization pattern

## Cursor

Integration style:

- Cursor rules
- MCP config where supported
- project-local `.akbp/` discovery

## OpenClaw

Integration style:

- workspace instructions
- memory flush bridge
- task/session crystallization
- MCP/CLI calls through first-class tools where possible

## Gemini CLI

Integration style:

- agent instruction file
- CLI/MCP calls
- local workspace discovery

## Adapter rule

Adapters must not invent their own memory format. They can add runtime-specific instructions, but durable artifacts must remain AKBP-compatible.
