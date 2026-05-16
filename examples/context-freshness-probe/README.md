# Context Freshness Probe

This example turns the context_freshness_probe contract from akbp discover into
a runnable adapter gate.

It proves two startup paths:

1. Verified sources plus cited akbp.session.start context can be trusted for
   planning.
2. Changed source evidence makes akbp.source.verify fail and makes strict
   startup context fail closed before an adapter plans from stale memory.

Run it from the repository root:

```bash
./examples/context-freshness-probe/run.sh
```

Adapters should run an equivalent gate before inherited or recalled AKBP context
influences planning. If the probe fails, continue without recalled AKBP memory
and keep write-capable methods disabled for that flow.
