# AKBP Schemas

AKBP schemas are public JSON Schema documents for the protocol artifacts.

## Current schemas

- `claim.schema.json`: atomic facts, decisions, preferences, warnings, questions, and observations.
- `entity.schema.json`: people, projects, repos, tools, concepts, workflows, systems, and other named objects.
- `relation.schema.json`: typed graph edges between entities or claims.
- `evidence.schema.json`: pointers to source spans, files, commits, messages, URLs, screenshots, PDFs, or transcripts.
- `source.schema.json`: immutable raw source records.
- `page.schema.json`: metadata for human-readable markdown pages.
- `audit-event.schema.json`: append-only operation history.
- `context-pack.schema.json`: compact retrieval output for agents.

## Schema IDs

Schema `$id` values use GitHub raw URLs so they resolve today.

Example:

```text
https://raw.githubusercontent.com/rohitg00/akbp/main/schemas/evidence.schema.json
```

If AKBP later owns a domain, update this document and the schemas in the same commit. Do not use non-resolving future domains in committed schemas.

## Knowledge Base Card

`schemas/akbp-card.schema.json` defines `akbp.json`, the machine-readable discovery card for an AKBP knowledge base.
