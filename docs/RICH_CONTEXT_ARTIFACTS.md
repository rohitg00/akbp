# Rich context artifacts

This note captures a strong AKBP use case from current agent-output research: agents should not only return linear text. For complex work, they should compile durable knowledge into small, inspectable HTML artifacts that future agents and humans can both use.

This is not about copying any specific project or author. The useful pattern is generic:

> Turn messy context into a portable, cited, interactive artifact that can be reviewed, edited, exported, and fed back into the agent loop.

## Why this fits AKBP

AKBP already stores the hard parts of durable agent knowledge:

- claims
- sources
- source hashes
- relations
- lifecycle state
- audit history
- export manifests
- context packs

A rich artifact is the human-facing view over those protocol objects.

Markdown is good for simple notes. HTML is better when the knowledge has shape:

- an annotated diff
- a decision map
- a timeline
- a system diagram
- a comparison matrix
- a postmortem
- a research brief
- a release readiness report
- a custom review form

AKBP can provide the trusted backing store, while the HTML page provides the review surface.

## Core AKBP use case

### Cited project brief

An agent starts with raw notes, source files, logs, issues, or transcripts.

AKBP stores:

- source records with hashes
- extracted claims with evidence
- relations between claims/entities
- lifecycle updates when decisions change

Then the agent generates a self-contained `artifact.html` that includes:

- executive summary
- cited claims
- expandable source snippets
- relation graph
- timeline of decisions
- unresolved questions
- review checklist
- export button for selected updates

The artifact does not become the source of truth. It is a generated review layer over AKBP files.

## Good artifact types for AKBP

### 1. Decision review page

Use when a team needs to understand why a project chose one path over another.

Page sections:

- current decision
- alternatives considered
- supporting claims
- contradicting claims
- source citations
- superseded decisions
- reviewer notes

AKBP backing objects:

- `claims/claims.jsonl`
- `graph/relations.jsonl`
- `raw/sources/sources.jsonl`
- `.akbp/audit.log.jsonl`

### 2. Agent handoff page

Use when one agent session must pass useful context to another.

Page sections:

- task summary
- what changed
- active constraints
- commands run
- evidence-backed decisions
- open risks
- recommended next actions

AKBP backing objects:

- context pack
- session crystallization result
- cited claims
- audit events

### 3. Pull request understanding page

Use when a reviewer needs spatial context, not a wall of text.

Page sections:

- files changed
- risk map
- annotated diff snippets
- affected entities
- related prior decisions
- test/validation status
- unresolved review questions

AKBP backing objects:

- registered PR diff/source
- claims about architectural constraints
- relations between modules/entities
- validation evidence

### 4. Postmortem page

Use when an incident or failed agent run should become reusable knowledge.

Page sections:

- timeline
- root causes
- decisions made
- durable lessons
- actions accepted/rejected
- claims to supersede
- follow-up tasks

AKBP backing objects:

- source logs/transcripts
- claims with confidence/status
- relation edges such as caused_by, blocks, supersedes
- audit events

### 5. Research map page

Use when the agent has gathered many sources and needs to make them navigable.

Page sections:

- ranked themes
- source cards
- claim clusters
- uncertainty notes
- contradiction table
- recommended AKBP changes

AKBP backing objects:

- imported sources
- research claims
- citation bundle
- export manifest

## Safety model

Generated HTML must be treated as an artifact, not trusted code.

Rules:

1. Default to static HTML, CSS, and minimal inline JavaScript.
2. No network calls by default.
3. No secrets, tokens, cookies, auth headers, private URLs, or environment dumps.
4. Include source ids and hashes, not raw sensitive content unless explicitly approved.
5. Make every proposed write export as JSONL first.
6. Require AKBP dry-run and approval before applying artifact-selected updates.
7. Store the artifact path in audit metadata when it influences a durable write.

## Protocol implication

AKBP should eventually define an optional artifact layer:

```text
artifacts/
  decision-review.html
  agent-handoff.html
  research-map.html
```

Each artifact should have a small metadata record:

```json
{
  "id": "artifact_release_review",
  "type": "decision_review",
  "path": "artifacts/release-review.html",
  "derived_from": ["source_release_notes", "claim_release_gate"],
  "created_at": "2026-05-11T00:00:00Z",
  "generator": "akbp-reference",
  "network_access": false,
  "proposes_writes": true
}
```

This can stay optional until the core claim/source/relation model is stable.

## Minimal implementation path

Start with docs and examples, not a large feature:

1. Add `examples/rich-context-artifact/`.
2. Create a small KB with sources, claims, and relations.
3. Generate a static `artifact.html` from those files.
4. Add an `updates.jsonl` export from selected review decisions.
5. Feed `updates.jsonl` through existing `import-check` and `import-apply` review gates.

This proves the loop without adding a browser runtime or new server.

## Why users will understand it

The product story is simple:

> AKBP is the source of truth. Rich artifacts are the review surface.

That gives users the best of both:

- machine-readable durable memory for agents
- human-readable interactive reviews for decisions, handoffs, PRs, research, and postmortems

## Demo idea

Title:

> From messy session notes to a cited interactive handoff

Flow:

1. initialize AKBP
2. register a session note as source
3. preview extracted claims
4. approve writes
5. generate `agent-handoff.html`
6. inspect citations and lifecycle state
7. export selected updates as JSONL
8. run `import-check`
9. apply only after approval

Success criterion:

A user should see that AKBP is not just memory storage. It is a trusted substrate for producing useful, reviewable project artifacts.

## Related pattern: markdown experience layer

A new adjacent pattern is emerging around improving markdown presentation without changing markdown itself. The useful idea for AKBP is simple:

> Keep the durable source format simple, but standardize the reading and review experience above it.

This is directly relevant because AKBP already uses markdown and JSONL as the durable substrate. Instead of replacing that with a heavier format, AKBP can define a better experience layer for people reviewing large generated context.

### What AKBP can borrow as a pattern

1. **Virtual pages**
   - Split long generated briefs at H1/H2 boundaries.
   - A single artifact can become a navigable multi-page review.

2. **Page navigation and outline**
   - Every AKBP-generated brief should provide page navigation.
   - H3-H6 headings inside the current page should become an outline.

3. **Preview/source toggle**
   - Reviewers should be able to see the rendered brief and the underlying markdown or JSONL proposals.

4. **Search across the artifact**
   - Long handoffs, postmortems, and research maps need in-artifact search.

5. **Code blocks with copy buttons**
   - Useful for command logs, JSONL tool calls, import-check results, and adapter snippets.

6. **Task lists as review controls**
   - Artifact checkboxes can represent review status, but durable writes still require AKBP approval.

7. **Document links stay local**
   - Links between generated AKBP briefs should open in the same viewer where possible.

### AKBP-specific twist

The experience layer should show protocol trust metadata that normal markdown viewers do not understand:

- claim id
- source id
- source hash
- claim status
- confidence
- lifecycle relation
- audit event
- import-check result
- approval state

So AKBP should not merely render markdown better. It should render cited project knowledge with trust cues.

### Practical implementation idea

Add a generated viewer artifact:

```text
artifacts/
  handoff.md
  handoff.html
  handoff.proposals.jsonl
```

The markdown remains readable and portable. The HTML adds navigation, outline, search, citations, source-hash badges, and export controls.

The proposals JSONL remains the only write path. It must pass `import-check` and approval before any durable write.

### Product framing

> Plain files stay the source of truth. The viewer makes them navigable, reviewable, and safe to act on.

This strengthens AKBP's position: it is not trying to invent another document format. It defines durable knowledge objects and can generate better review experiences from them.
