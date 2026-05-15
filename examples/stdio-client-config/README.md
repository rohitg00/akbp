# Stdio client config

This example shows how an adapter author can generate a pasteable AKBP stdio JSONL configuration before writing any runtime glue.

The generated config makes the trust boundary visible:

- call `akbp.capabilities` before assuming methods or schemas
- run `akbp.doctor` before trusting startup retrieval or write flows
- request either `read_only` or `write_review`
- retrieve context with `akbp.session.start`
- keep durable writes blocked unless the adapter implements dry-run review and `approved:true`

## Run

From the repository root:

```bash
examples/stdio-client-config/run.sh
```

Expected success marker:

```text
AKBP stdio client config example passed
```

## What it proves

- `akbp client-config` emits valid JSON for both read-only and reviewed-write adapters
- the config starts with capability negotiation instead of hard-coded assumptions
- the config exposes a health check that adapters can map to setup warnings and next steps
- reviewed-write configs keep the dry-run and approval boundary explicit
