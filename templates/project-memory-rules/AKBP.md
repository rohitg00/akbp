# AKBP project memory rules

This file tells agents and maintainers what belongs in durable project memory.

AKBP memory is local, review-gated, cited, and portable. It is not raw chat history, private logs, or an unreviewed scratchpad.

## Durable knowledge

Store knowledge when it will help a later agent or maintainer avoid re-discovery:

- stable project decisions
- active architecture constraints
- validated setup steps
- recurring failure modes and fixes
- release or migration rules
- source-backed product requirements
- superseded decisions that future work may otherwise repeat

Do not store guesses, vague preferences, raw transcripts, private credentials, personal data, or temporary plan details that will be stale after the current task.

## Evidence rule

Every durable claim should cite evidence.

Preferred evidence:

- repository files
- issue or pull request notes
- design documents
- release notes
- reviewed session summaries
- local notes approved for project memory

If evidence is missing, register a source first or keep the claim as a draft outside durable memory.

## Write policy

Agents may propose memory. Durable writes require review.

Required flow:

1. Retrieve existing context before proposing new memory.
2. Preview write-capable operations with `dry_run:true`.
3. Show the review fields, warnings, planned writes, and affected files.
4. Apply only after a person or trusted local policy approves the unchanged request.
5. Use request-level `approved:true` for the apply call.
6. Rebuild retrieval indexes when the approved write changes searchable memory.

Do not apply session-end memory automatically. Session-end memory must be previewed and reviewed like any other durable write.

## Approval policy

Default approval source:

```text
Project maintainer or explicit local policy
```

The approver should check:

- the claim is useful after this session
- the claim is specific enough to retrieve later
- evidence exists and is safe to cite
- no secrets or private data are included
- stale knowledge is superseded or contradicted instead of silently overwritten

## Never store

Never store:

- API keys, tokens, cookies, passwords, or auth headers
- private user data unless the project explicitly permits it
- raw private chat logs
- unredacted error output containing secrets
- credentials embedded in URLs
- speculation presented as fact
- runtime-only implementation details that do not belong in portable project memory

Use summaries and citations instead of copying sensitive source material.

## Lifecycle rule

When knowledge changes, preserve history:

- use a new claim for the updated decision
- mark the old claim as superseded or contradicted
- cite the evidence that justifies the change
- keep source hashes and audit events intact

Do not delete old reviewed knowledge just because it is stale. Later agents need to know what changed and why.

## Validation

Before sharing a knowledge base or wiring an adapter, run:

```bash
akbp doctor
akbp source verify
akbp conformance --level 2
```

For repository changes, run the project validation gate before committing.

## Adapter rule

Adapters translate runtime events into AKBP reads and review-gated writes. They must not create another durable memory format.

At startup, adapters should retrieve cited context. At shutdown, they may preview session memory, but they must not apply it without review and `approved:true`.
