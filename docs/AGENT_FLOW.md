# Agent Flow

This page shows a minimal end-to-end AKBP workflow for agents.

## CLI flow

```bash
python3 cli/akbp.py --path ./my-kb init
python3 cli/akbp.py --path ./my-kb ingest notes.md --claim "Database migrations ship in small verified batches." --claim-type decision
python3 cli/akbp.py --path ./my-kb index --incremental
python3 cli/akbp.py --path ./my-kb search "database migrations rollback"
python3 cli/akbp.py --path ./my-kb context "prepare the next migration release"
python3 cli/akbp.py --path ./my-kb cite claim_small_verified_migrations
```

## JSONL tool-server flow

Start write-capable calls with dry-run when the runtime does not already have durable-memory approval:

```json
{"id":"1","method":"akbp.ingest","path":"./my-kb","dry_run":true,"params":{"file":"notes.md","claim":"Database migrations ship in small verified batches.","claim_type":"decision"}}
```

After review or approval, repeat the same request without `dry_run`, then refresh retrieval state and fetch context:

```json
{"id":"2","method":"akbp.ingest","path":"./my-kb","params":{"file":"notes.md","claim":"Database migrations ship in small verified batches.","claim_type":"decision"}}
{"id":"3","method":"akbp.index","path":"./my-kb","params":{"incremental":true}}
{"id":"4","method":"akbp.search","path":"./my-kb","params":{"query":"database migrations rollback","limit":5}}
{"id":"5","method":"akbp.context","path":"./my-kb","params":{"task":"prepare the next migration release","limit":5}}
```

## Safety notes

- Run write methods with `dry_run: true` when an agent is unsure.
- Ingest redacts common token and key patterns before writing imported pages.
- Claims should cite source IDs, not uncited memory.
- Local indexes are engine-owned state and can be rebuilt from JSONL and markdown artifacts.

## Runnable example

See `examples/end-to-end-agent-flow/` for a compact knowledge base containing source records, one evidence-backed claim, entities, a relation, audit history, and wiki pages.
