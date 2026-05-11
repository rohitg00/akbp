# AKBP workflow

AKBP works best when users can follow a named, reviewable path instead of thinking in raw tool methods.

Use this page as the human-facing workflow that adapter docs, demos, and templates can point to.

## One-line workflow

Discover evidence -> preview memory -> approve write -> recall cited context -> update lifecycle -> export bundle.

## 1. Discover evidence

Goal: collect the source material that makes a future claim trustworthy.

Typical inputs:

- release notes
- architecture notes
- issue summaries
- session transcripts
- migration plans
- user-approved decisions

User-facing question:

> What did we learn that future agents should not re-derive?

AKBP artifacts:

- `raw/sources/sources.jsonl`
- optional copied files under `raw/`
- source hashes for verification

## 2. Preview memory

Goal: let the agent propose durable knowledge without writing it silently.

The preview should show:

- proposed claim text
- claim type
- evidence references
- redaction status
- whether review is required
- the exact apply instruction

User-facing question:

> Is this worth making durable project knowledge?

AKBP artifacts:

- dry-run result
- structured preview metadata
- no durable claim write yet

## 3. Approve write

Goal: turn a reviewed proposal into a durable claim.

Approval should be explicit at request level. Agents can suggest, but reviewed writes are the trust boundary.

User-facing question:

> Has a person or trusted policy approved this memory?

AKBP artifacts:

- `claims/claims.jsonl`
- `.akbp/audit.log.jsonl`
- updated `wiki/log.md`

## 4. Recall cited context

Goal: give the next agent session compact, evidence-backed context instead of a vague chat-history summary.

The recalled context should include:

- relevant claims
- citations
- source ids
- status/lifecycle hints
- enough text for the agent to act safely

User-facing question:

> What should the next agent know before it starts work?

AKBP artifacts:

- context pack result
- search index under `.akbp/`, rebuildable from source artifacts

## 5. Update lifecycle

Goal: preserve history while marking old or conflicting knowledge clearly.

Use lifecycle updates when:

- a decision replaces an older decision
- two claims conflict
- a workflow becomes stale
- evidence changes or disappears

User-facing question:

> Should we supersede, contradict, archive, or verify this knowledge?

AKBP artifacts:

- `supersedes` and `superseded_by` fields on claims
- `graph/relations.jsonl`
- conformance level 3 lifecycle checks

## 6. Export bundle

Goal: make project knowledge portable across tools, repos, or review flows.

A bundle should include:

- card
- claims
- sources
- entities
- relations
- manifest
- safety flags
- verification metadata

User-facing question:

> Can another agent or reviewer inspect this bundle before accepting it?

AKBP artifacts:

- export JSON
- export-check result
- import-check result before any apply

## Demo script shape

A good AKBP demo should show all six stages in under six minutes:

1. initialize an empty knowledge base
2. add a source note
3. preview a claim with dry-run
4. apply the reviewed claim
5. recall context with citation
6. supersede or contradict a claim
7. export and check the bundle

## Public framing

Use this phrasing:

> AKBP makes project knowledge reviewable before it becomes durable, cited when it is recalled, and explicit when it changes.

Avoid this phrasing:

> AKBP is magic memory for agents.

That is too vague and hides the actual product: reviewed files, citations, lifecycle relations, audit logs, and portable bundles.
