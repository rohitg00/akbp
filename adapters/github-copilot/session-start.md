# GitHub Copilot Session Start

Use this sequence at the start of a project session or before a substantial task.

## 1. Discover AKBP

Look for `akbp.json` in the repository root or parent directories. If it is missing, continue without durable project knowledge and suggest `akbp init` only when the user wants persistent memory.

## 2. Discover capabilities

```json
{"id":"copilot-caps","method":"akbp.capabilities","params":{"client":"github-copilot-adapter","requires":["method_param_schemas","capability_negotiation","write_apply_requires_approval"]}}
```

If negotiation is not satisfied, keep read-only behavior and tell the user which feature is missing.

## 3. Retrieve cited context

```json
{"id":"copilot-session-start","method":"akbp.session.start","path":".","params":{"task":"current coding task","limit":8}}
```

Use returned citations when they affect plans, code changes, release steps, or user-facing recommendations.

Follow `docs/AGENT_FLOW.md` for the canonical startup loop.
