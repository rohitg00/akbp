# Protocol Standard Gap Analysis

This document benchmarks AKBP against three useful protocol references:

- repository instruction files: simple file convention with immediate adoption path
- a widely adopted tool protocol: formal schema, documentation, SDK ecosystem, versioned specification
- a widely adopted agent communication protocol: discovery, lifecycle, transports, SDKs, samples, governance

## What these protocols do well

### repository instruction files

repository instruction files wins because the adoption surface is tiny.

A project can add one predictable file and every agent gets value. There is no server, package manager, hosted service, or migration step required.

Pattern to copy:

- one obvious file name
- one obvious location
- works in any repo
- human-readable first
- useful before tooling exists

AKBP equivalent:

- define `AKBP.md` as the human-readable entry point
- define `.akbp/config.json` only for tools
- make Level 0 adoption possible with markdown only

### tool protocol

tool protocol wins because it has a formal specification and protocol schema, plus docs that make implementers confident.

Pattern to copy:

- versioned spec
- canonical schema source
- generated compatibility artifacts
- clear client/server roles
- explicit capability negotiation
- contribution process for spec evolution

AKBP equivalent:

- versioned protocol releases, starting with `spec/2026-04-29/`
- generated JSON Schema bundle
- AKBP engine/client roles
- capability manifest
- proposal process for protocol changes

### agent communication

agent communication wins because it treats interoperability like a product, not just a document.

Pattern to copy:

- agent discovery through machine-readable cards
- task lifecycle
- multiple transports
- SDKs and samples
- enterprise/security posture
- contribution and governance docs

AKBP equivalent:

- `akbp.json` knowledge-base card for discovery
- memory lifecycle and sync lifecycle as first-class state machines
- tool protocol first, CLI second, HTTP later
- reference server and examples
- security and privacy policy

## Current AKBP strengths

AKBP already has the right wedge:

- clear problem: agents start with amnesia
- clear scope: durable agent knowledge, not agent messaging or tool calling
- local-first artifacts: markdown and JSONL
- evidence-backed claims
- lifecycle states
- adapter direction for coding agents
- tool contract direction
- compliance levels
- small CLI proving the concept

The roadmap is directionally correct.

## Current gaps

### 1. No single adoption artifact yet

A protocol needs a five-minute adoption path.

Missing:

- `AKBP.md` root file convention
- `.akbp/config.json` schema as the tool-readable manifest
- `akbp.json` knowledge-base card for discovery

### 2. No versioned specification layout

Current `SPEC.md` is useful, but standards need stable versioned specs.

Missing:

- `spec/latest.md`
- `spec/2026-04-29/spec.md`
- changelog of protocol changes
- compatibility policy

### 3. No conformance suite

A standard needs a way to say “this implementation is AKBP-compatible.”

Missing:

- compliance test fixtures
- `akbp conformance` command
- Level 0 to Level 5 test matrix
- adapter certification checklist

### 4. No discovery model

tool protocol has servers. agent communication has Agent Cards. AKBP needs Knowledge Base Cards.

Missing:

- `akbp.json` discovery file
- supported capabilities
- supported retrieval modes
- privacy scopes
- schema version
- adapter hints

### 5. No governance story

Public protocols need transparent evolution.

Missing:

- `CONTRIBUTING.md`
- `SECURITY.md`
- `GOVERNANCE.md`
- proposal process for spec changes
- AI contribution disclosure policy

### 6. No reference server yet

The CLI is useful, but agents will adopt through tool protocol/tool interfaces.

Missing:

- tool-server reference implementation
- documented tool request/response examples
- adapter samples that call the server

### 7. No install path

A protocol repository needs a one-command local demo.

Missing:

- Python package metadata or install script
- `uvx akbp` or `pipx install akbp` target
- example repo fixture
- quickstart verified in CI

## Roadmap correction

The old roadmap had the right components but the wrong order.

Before adding advanced retrieval, AKBP needs protocol credibility:

1. adoption convention
2. versioned spec
3. knowledge-base card
4. conformance tests
5. reference tool-server implementation
6. adapters
7. retrieval upgrades

Advanced vector search is not the moat. Interoperability and conformance are.

## Target standard

AKBP should be the protocol that answers:

```text
How does any agent discover, read, update, cite, and synchronize durable knowledge without locking into one memory product?
```

That means AKBP must define:

- files on disk
- schemas on wire
- lifecycle rules
- discovery card
- capability negotiation
- conformance levels
- security expectations
- reference implementation

## Non-goals

AKBP should not become:

- a hosted notes app
- a vector database product
- a replacement for tool protocol
- a replacement for agent communication
- an agent framework
- a generic RAG framework

AKBP complements them:

- Repository instruction files tell coding agents how to work in a repo.
- Tool protocols let agents call tools and retrieve context.
- Agent communication protocols let agents collaborate.
- AKBP gives agents durable, portable knowledge they can cite and update.
