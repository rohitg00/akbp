# AKBP tool protocol Contract

## Goal

Expose AKBP through stable tool calls so any compatible agent can read, write, cite, and maintain a shared knowledge base.

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

- tool protocol write tools must support dry-run mode.
- Destructive actions must be reversible.
- Secret-like strings must be redacted before writes unless explicitly allowed by config.
- Private scopes must not be returned to agents outside their configured visibility.

## `akbp.export`

Return a portable bundle of protocol artifacts: card, claims, sources, entities, and relations. Local indexes and engine-owned state are excluded.

## `akbp.audit`

Return recent audit events, optionally filtered by event type.

## JSONL reference server

`tool-server/akbp_tool_server.py` is a dependency-free JSONL server for local agent integrations. It reads one JSON request per line and writes one JSON response per line.

Supported methods in the first server slice:

- `akbp.capabilities`
- `akbp.status`
- `akbp.query`
- `akbp.context`
- `akbp.index`
- `akbp.search`
- `akbp.remember`
- `akbp.conformance`
- `akbp.export`
- `akbp.audit`
- `akbp.cite`
- `akbp.source.add`
- `akbp.ingest`
- `akbp.supersede`
- `akbp.contradict`

Request and response envelopes are specified in:

- `schemas/tool-request.schema.json`
- `schemas/tool-response.schema.json`
- `schemas/tool-methods.schema.json`

`akbp.capabilities` returns these schema URLs under `result.schemas`, and returns each method's `params_schema` reference when a method-specific contract exists.

`tool-methods.schema.json` defines the first method-specific parameter contracts for:

- `akbp.query`
- `akbp.context`
- `akbp.index`
- `akbp.search`
- `akbp.remember`
- `akbp.source.add`
- `akbp.ingest`
- `akbp.supersede`
- `akbp.contradict`

Every response uses the same envelope:

```json
{
  "id": "request-id",
  "ok": true,
  "result": {},
  "error": null
}
```

Errors are structured:

```json
{
  "id": "request-id",
  "ok": false,
  "result": null,
  "error": {
    "code": "unknown_method",
    "message": "unknown method: akbp.missing",
    "details": {
      "available_methods": []
    }
  }
}
```

## Write-mode safety

Write-capable methods must be treated as reviewable operations by default.

Agents should:

1. call `akbp.capabilities` first and check the advertised method list and `params_schema` references
2. use request-level `dry_run: true` before the first write in a session
3. show the planned write to the user or calling runtime when approval is required
4. repeat the same request without `dry_run` only after approval or trusted local policy
5. use project-local scope unless the user explicitly asks for team or public memory
6. cite evidence for durable claims and avoid storing transient logs
7. redact secret-like strings before sending write requests

Write methods support request-level dry run:

```json
{"id":"1","method":"akbp.remember","path":".","dry_run":true,"params":{"text":"Agents need rollback paths","type":"workflow","evidence":["release-notes.md"]}}
```

Dry-run write responses return planned command arguments and do not mutate the knowledge base. Clients should render them as a reviewable change, not as committed memory.

Importing a local file through the JSONL server should also start with dry-run when the caller is unsure about scope or content sensitivity:

```json
{"id":"2","method":"akbp.ingest","path":".","dry_run":true,"params":{"file":"notes.md","claim":"The project ships small verified batches","claim_type":"decision"}}
```

Agents can also manage the local search index and query it:

```json
{"id":"3","method":"akbp.index","path":".","params":{"incremental":true}}
{"id":"4","method":"akbp.search","path":".","params":{"query":"rollback release","limit":5}}
```

