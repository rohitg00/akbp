# Standards Track

AKBP needs a protocol process, not just a software roadmap.

## Protocol artifacts

A standards-grade AKBP release should include:

- specification document
- JSON schemas
- discovery card schema
- lifecycle state machine
- capability model
- conformance fixtures
- reference CLI
- reference tool-server implementation
- adapter examples
- security guidance
- changelog

## Versioning

Protocol versions use date-based folders:

```text
spec/
  latest.md
  2026-04-29/
    spec.md
    schemas/
```

`spec/latest.md` points to the newest stable version.

Draft changes happen in:

```text
spec/draft/
```

## Compatibility policy

Patch-compatible changes:

- documentation clarifications
- optional fields
- new enum values marked experimental
- new examples or fixtures

Breaking changes:

- removing fields
- changing required fields
- changing lifecycle semantics
- changing discovery semantics
- changing conformance requirements

Breaking changes require a new dated protocol version.

## Proposal process

Major changes should use AKBP Enhancement Proposals.

```text
proposals/
  0001-knowledge-base-card.md
  0002-conformance-levels.md
```

Each proposal should include:

- problem
- proposed change
- alternatives considered
- compatibility impact
- security/privacy impact
- reference implementation plan
- conformance tests required

## Conformance levels

AKBP conformance should be testable.

### Level 0: File convention

- has `AKBP.md`
- has valid `.akbp/config.json` or `akbp.json`
- exposes human-readable project knowledge

### Level 1: Structured memory

- valid claims
- valid evidence
- valid sources
- stable IDs

### Level 2: Retrieval

- query returns ranked results
- context packs match schema
- citations are preserved

### Level 3: Lifecycle

- claims can be superseded
- contradictions are represented
- audit events are recorded

### Level 4: Tool protocol

- tool calls implemented
- capability negotiation supported
- errors are structured

### Level 5: Collaboration

- sync semantics defined
- conflict handling works
- scopes and privacy are enforced

## Governance

Before a public launch, add:

- `CONTRIBUTING.md`
- `SECURITY.md`
- `GOVERNANCE.md`
- `CODE_OF_CONDUCT.md`
- issue templates
- pull request template

Protocol changes need examples and tests, not just prose.
