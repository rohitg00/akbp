# Agent Flow

This page shows a minimal end-to-end AKBP workflow for agents.

## CLI flow

```bash
python3 cli/akbp.py --path ./my-kb init
python3 cli/akbp.py --path ./my-kb ingest notes.md --claim "Database migrations ship in small verified batches." --claim-type decision --dry-run
python3 cli/akbp.py --path ./my-kb ingest notes.md --claim "Database migrations ship in small verified batches." --claim-type decision
python3 cli/akbp.py --path ./my-kb index --incremental
python3 cli/akbp.py --path ./my-kb search "database migrations rollback"
python3 cli/akbp.py --path ./my-kb context "prepare the next migration release"
python3 cli/akbp.py --path ./my-kb cite claim_small_verified_migrations
```

The first ingest command is a preview. Review the redaction status, extracted signals, claim ids, and would-write paths before repeating it without `--dry-run`.

## JSONL tool-server flow

Start write-capable calls with dry-run when the runtime does not already have durable-memory approval. Treat `review_required` and `apply_instruction` from dry-run responses as the runtime boundary before applying writes. For `akbp.ingest`, the dry-run response returns the same redacted preview fields as the CLI preview:

```json
{"id":"1","method":"akbp.ingest","path":"./my-kb","dry_run":true,"params":{"file":"notes.md","claim":"Database migrations ship in small verified batches.","claim_type":"decision"}}
```

After review or approval, repeat the same request with request-level `approved:true` and without `dry_run`, then refresh retrieval state and fetch context:

```json
{"id":"2","method":"akbp.ingest","path":"./my-kb","approved":true,"params":{"file":"notes.md","claim":"Database migrations ship in small verified batches.","claim_type":"decision"}}
{"id":"3","method":"akbp.index","path":"./my-kb","approved":true,"params":{"incremental":true}}
{"id":"4","method":"akbp.search","path":"./my-kb","params":{"query":"database migrations rollback","limit":5}}
{"id":"5","method":"akbp.context","path":"./my-kb","params":{"task":"prepare the next migration release","limit":5}}
```

At session end, preview transcript crystallization before writing durable session memory:

```json
{"id":"6","method":"akbp.crystallize_session","path":"./my-kb","dry_run":true,"params":{"transcript":"session.md","apply":true}}
```

After review or approval, apply the same crystallization and refresh the index:

```json
{"id":"7","method":"akbp.crystallize_session","path":"./my-kb","approved":true,"params":{"transcript":"session.md","apply":true}}
{"id":"8","method":"akbp.index","path":"./my-kb","approved":true,"params":{"incremental":true}}
```

## Safety notes

- Run write methods with `dry_run: true` when an agent is unsure.
- Check JSONL exports with `akbp import-check export.jsonl` before turning them into durable claims or sources. Use `--fail-on-rejected` for CI or adapter gates that must stop on any rejected object.
- Preview accepted source and claim imports with `akbp import-apply export.jsonl --dry-run`; apply with `--approved` only after reviewing the dry-run output.
- Before applying imports, confirm `accepted_count`, `rejected_count`, `error_count`, `would_write.sources`, and `would_write.claims`.
- Stop instead of applying when import check reports rejected objects, malformed JSONL, unsupported kinds, or secret-like values.
- Start source imports with `akbp ingest --dry-run` or JSONL `akbp.ingest` plus request-level `dry_run:true`, then apply only after review with request-level `approved:true`.
- Ingest redacts common token and key patterns before writing imported pages and optional claims.
- Claims should cite source IDs, not uncited memory.
- Local indexes are engine-owned state and can be rebuilt from JSONL and markdown artifacts.

## Runnable example

See `examples/end-to-end-agent-flow/` for a compact knowledge base containing source records, one evidence-backed claim, entities, a relation, audit history, and wiki pages.

## Source intake playbook

See `examples/source-intake/README.md` for a review-first flow that turns files, transcripts, and JSONL exchanges into durable AKBP sources and claims.
