# Proposal 0001: Knowledge Base Card

## Problem

Agents need a predictable way to discover what an AKBP knowledge base supports before reading or writing durable knowledge.

## Proposed change

Define `akbp.json` as the machine-readable Knowledge Base Card.

The card declares:

- schema version
- knowledge base name
- portable artifact paths
- capabilities
- retrieval modes
- transports
- privacy defaults

## Compatibility impact

This is additive. Existing markdown-only knowledge bases can become Level 0 compatible by adding `AKBP.md` and `akbp.json`.

## Security and privacy impact

The card includes privacy defaults and secret-redaction expectations. Implementations should treat these as minimum safety requirements, not complete policy enforcement.

## Reference implementation plan

The reference CLI should:

- create `akbp.json` during `akbp init`
- validate required fields during `akbp lint`
- validate Level 0 compatibility during `akbp conformance --level 0`

## Conformance tests required

- card exists
- required fields exist
- required artifact paths exist
- required capabilities exist
- `AKBP.md` exists and starts with a level-one heading
