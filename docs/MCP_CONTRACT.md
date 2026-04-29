---
title: "AKBP MCP Contract"
type: "mcp-contract"
status: "draft"
tags:
  - "akbp"
  - "mcp"
created: "2026-04-29"
---

# AKBP MCP Contract

## Goal

Expose AKBP through stable MCP tools so any compatible agent can read, write, cite, and maintain a shared knowledge base.

## Tool naming

All tools use the `akbp.` prefix.

## Tools

### akbp.search

Search pages, claims, entities, and evidence.

Input:

```json
{
  "query": "string",
  "limit": 10,
  "modes": ["bm25", "vector", "graph"],
  "scope": "default"
}
```

Output:

```json
{
  "results": [
    {
      "id": "claim_...",
      "type": "claim",
      "title": "string",
      "summary": "string",
      "score": 0.91,
      "citations": []
    }
  ]
}
```

### akbp.get_context

Return compact context for an agent task.

Input:

```json
{
  "task": "string",
  "agent": "codex",
  "project": "optional-project-id",
  "max_tokens": 3000
}
```

Output:

```json
{
  "context": "markdown string",
  "claims": [],
  "warnings": [],
  "citations": []
}
```

### akbp.remember

Write a claim or observation.

Input:

```json
{
  "text": "string",
  "type": "observation|decision|preference|workflow|fact",
  "evidence": [],
  "scope": "private|project|team|public"
}
```

### akbp.crystallize_session

Convert a session transcript into durable knowledge.

Input:

```json
{
  "transcript": "string",
  "agent": "string",
  "project": "string",
  "mode": "dry_run|apply"
}
```

Output:

```json
{
  "claims_created": 0,
  "claims_updated": 0,
  "pages_updated": [],
  "relations_created": 0,
  "warnings": []
}
```

### akbp.cite

Return evidence for a claim or answer.

### akbp.supersede

Mark an old claim as replaced by a newer claim.

### akbp.lint

Run health checks.

### akbp.archive

Archive low-value or stale claims without deleting evidence.

## Safety defaults

- MCP write tools must support dry-run mode.
- Destructive actions must be reversible.
- Secret-like strings must be redacted before writes unless explicitly allowed by config.
- Private scopes must not be returned to agents outside their configured visibility.
