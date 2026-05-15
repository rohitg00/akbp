# Tool-protocol bridge preflight

This example gives tool-protocol hosts and local assistant bridges a read-only
preflight before exposing AKBP context as host tools.

Run it from the repository root:

```bash
./examples/tool-protocol-bridge/run.sh
```

Expected success markers:

```text
AKBP tool-protocol bridge preflight
bridge config contract ok
read-only bridge startup ok
read-only bridge context ok
direct write blocked ok
AKBP tool-protocol bridge preflight passed
```

## What it proves

- `akbp client-config --profile read-only` emits a bridge-ready wrapper map.
- Every `tool_protocol_bridge.forward_tools` entry maps to the read-only
  allowlist and preserves response fields.
- `tool_protocol_bridge.host_tool_manifest` gives tool-protocol hosts a concrete
  read-only tool list, input schema refs, stdio command, and response fields to
  preserve without inventing another memory store.
- Write-capable AKBP methods stay in `blocked_write_methods` unless the host
  implements a separate reviewed-write surface.
- The bridge can call `akbp.capabilities`, `akbp.doctor`, and
  `akbp.session.start` before planning from memory.
- A direct `akbp.remember` call without approval returns
  `error.code:"approval_required"` instead of writing durable memory.

Use this before wiring AKBP into a tool server, IDE command palette, desktop
assistant, or hosted tool bridge. The bridge should stay read-only until this
preflight, the structured output harness, and any host-specific review UI checks
pass.
