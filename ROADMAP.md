# AKBP Roadmap

The roadmap is being corrected around protocol credibility first, implementation depth second.

AKBP should become the durable knowledge layer that complements:

- repository instruction files for repo-local agent instructions
- tool protocol for tool/context access
- agent communication for agent-to-agent collaboration

## v0.1: Protocol foundation

Status: mostly complete.

- README
- SPEC
- architecture docs
- JSON schemas
- example knowledge bases
- tool contract
- adapter contracts
- benchmark definition
- reference CLI skeleton

## v0.2: Adoption convention and discovery

Goal: make AKBP adoptable in five minutes.

- define `AKBP.md` as the human-readable entry point
- define `akbp.json` Knowledge Base Card
- define `.akbp/config.json` for embedded/local engines
- add schema for Knowledge Base Card
- add `akbp init --level 0`
- add minimal example repo fixture
- add docs comparing AKBP with repository instruction files, tool protocol, and agent communication

## v0.3: Versioned specification and governance

Goal: move from project docs to protocol-standard shape.

- create `spec/latest.md`
- create dated spec folder under `spec/YYYY-MM-DD/`
- add changelog
- add compatibility policy
- add AKBP Enhancement Proposal process
- add `CONTRIBUTING.md`
- add `SECURITY.md`
- add `GOVERNANCE.md`
- add issue and PR templates

## v0.4: Conformance suite

Goal: make compatibility testable.

- define Level 0 to Level 5 conformance checks
- add `akbp conformance`
- add fixture knowledge bases
- validate schemas, IDs, citations, lifecycle states, and context packs
- publish adapter certification checklist

## v0.5: tool-server reference implementation

Goal: give agents a standard tool interface.

- `akbp.search`
- `akbp.get_context`
- `akbp.remember`
- `akbp.crystallize_session`
- `akbp.cite`
- `akbp.supersede`
- `akbp.lint`
- capability negotiation
- structured errors

## v0.6: Agent adapters

Goal: prove AKBP works across real agent runtimes.

- Claude Code
- Codex
- Cursor
- OpenClaw
- Gemini CLI
- repository instruction-file integration pattern

## v0.7: Retrieval and sync upgrades

Goal: improve quality after the standard surface is solid.

- SQLite index
- BM25
- optional vector search
- graph traversal
- rank fusion
- sync semantics
- conflict handling

## v1.0: Stable protocol release

Goal: credible external adoption.

- stable versioned spec
- passing conformance suite
- reference CLI
- reference tool-server implementation
- at least three working adapters
- security guidance
- public examples
- benchmark harness
