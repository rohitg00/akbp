# Knowledge Base Card

AKBP needs a discovery artifact similar in spirit to tool-server implementation capabilities and agent communication Agent Cards.

The proposed file is:

```text
akbp.json
```

or, for embedded repository use:

```text
.akbp/config.json
```

## Purpose

A Knowledge Base Card lets an agent discover:

- what protocol version is supported
- where portable artifacts live
- which capabilities are available
- which retrieval modes are available
- which scopes are safe to read or write
- which tools or transports are exposed

## Minimal example

```json
{
  "schema_version": "2026-04-29",
  "name": "example-akbp",
  "description": "Example AKBP knowledge base",
  "root": ".",
  "artifacts": {
    "wiki": "wiki/",
    "claims": "claims/claims.jsonl",
    "entities": "graph/entities.jsonl",
    "relations": "graph/relations.jsonl",
    "sources": "raw/sources/"
  },
  "capabilities": {
    "remember": true,
    "retrieve": true,
    "crystallize": true,
    "supersede": false,
    "audit": true
  },
  "retrieval": ["keyword"],
  "transports": ["cli"],
  "privacy": {
    "default_scope": "local",
    "secret_redaction": "required"
  }
}
```

## Required fields

- `schema_version`
- `name`
- `root`
- `artifacts`
- `capabilities`

## Design requirement

A Level 0 AKBP knowledge base must be useful even if no server is running.
