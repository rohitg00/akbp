# AKBP use cases

AKBP is useful when an agent needs durable project knowledge that can be reviewed, cited, exported, and reused by future sessions or different tools.

This page maps the public examples to real use cases people can understand quickly.

## 1. Repo memory for coding agents

**Problem:** every agent session rereads issues, PRs, release notes, and docs from scratch.

**AKBP use case:** capture reviewed project facts, decisions, and workflows as cited claims.

**Demo:** `examples/repo-memory-demo/`

**What it proves:**

- project artifacts become durable knowledge
- later sessions retrieve context with citations
- the agent does not rely only on chat history

## 2. Multi-agent consistency

**Problem:** different agents make conflicting decisions because they do not share reviewed context.

**AKBP use case:** one agent records a decision, another retrieves it, then supersedes it explicitly when the decision changes.

**Demo:** `examples/multi-agent-consistency-demo/`

**What it proves:**

- prior decisions are visible to the next runtime
- changed decisions keep lifecycle history
- supersession is explicit instead of silent overwrite

## 3. Inherited repo intake

**Problem:** coding agents often enter an unfamiliar repo with stale summaries, weak handoff notes, or no trusted project memory.

**AKBP use case:** run `akbp discover`, `akbp doctor --profile read-only`, and `akbp.session.start` before planning. If the knowledge base is missing, unindexed, uncited, or not adapter-ready, stay read-only and show the setup gaps instead of inventing project history.

**Demo:** `examples/session-start-harness/`

**What it proves:**

- an agent can find the nearest AKBP folder before trusting memory
- adapter readiness gates planning on cited startup context
- unfamiliar repos get a safe first step instead of automatic durable writes

## 4. Memory quality benchmark

**Problem:** agent memory claims are usually vague and hard to evaluate.

**AKBP use case:** score memory behavior against concrete checks: cited write, cited retrieval, supersession, export-check, and conformance.

**Demo:** `examples/akbp-bench/`

**What it proves:**

- memory quality can be tested
- benchmarks can use real protocol artifacts
- AKBP can grow into a reusable evaluation harness

## 5. Memory CI for teams

**Problem:** project memory can rot, leak unsafe content, or drift away from source evidence.

**AKBP use case:** CI validates lint, source verification, conformance, export bundles, incoming JSONL proposals, and dry-run apply.

**Demo:** `examples/memory-ci/`

**What it proves:**

- memory can have quality gates like code
- unsafe imports are checked before apply
- teams can enforce review-gated writes

## 6. Rich handoff and review artifacts

**Problem:** long agent summaries are hard to review and often mix facts, guesses, and proposed updates.

**AKBP use case:** generate a static review artifact from AKBP objects while keeping JSONL proposals as the only durable write path.

**Demo:** `examples/rich-context-artifact/`

**What it proves:**

- humans get a navigable review surface
- AKBP remains the source of truth
- proposed updates still pass import-check and approval gates

## 7. Knowledge base health snapshot

**Problem:** users and adapters need a fast way to see whether a knowledge base is useful, stale, indexed, and source-backed.

**AKBP use case:** run `akbp status` or `akbp.status` to get counts, latest claims, source verification health, index presence, audit count, and conformance level.

**What it proves:**

- memory health can be inspected without reading raw JSONL first
- dashboards and adapters can use one stable status payload
- source drift is visible before agents trust stale knowledge

## 8. Adapter integration

**Problem:** agent runtimes need a predictable way to request context, propose writes, and close sessions without inventing their own memory format.

**AKBP use case:** call JSONL tool methods for capability discovery, context retrieval, dry-run writes, approved writes, and session-end crystallization.

**Demo:** `examples/adapter-lifecycle/`

**What it proves:**

- adapters can integrate without a hosted service
- write safety is protocol-level behavior
- session memory becomes portable files

## 9. Portable knowledge bundles

**Problem:** memory is trapped in one tool or workspace.

**AKBP use case:** export a bundle, verify hashes and counts, then import checked JSONL into another knowledge base.

**Demo:** `examples/portable-bundle/`

**What it proves:**

- project knowledge can move between tools
- bundles can be checked before trust
- import is review-gated

## 10. Existing memory migration

**Problem:** useful facts already live in notes, agent memory exports, and prior tool stores, but bulk-importing them blindly creates stale or uncited memory.

**AKBP use case:** convert a reviewed line-oriented export into source and claim records, reject unsupported or uncited records, preview the write, then apply only after approval.

**Demo:** `examples/existing-memory-migration/`

**What it proves:**

- existing memory can become portable AKBP artifacts
- missing evidence is rejected before import
- migration stays review-gated instead of becoming a memory dump

## 11. Read-only adapter rollout

**Problem:** new adapters often need safe retrieval first, before they have enough UI to review durable writes.

**AKBP use case:** discover `akbp.capabilities`, use `result.profiles.read_only` as the method allowlist, retrieve cited context, and block write methods locally until review UX exists.

**Demo:** `examples/read-only-adapter/`

**What it proves:**

- adapters can ship context retrieval before write support
- read-only methods are discoverable instead of hand-maintained
- write-capable calls stay blocked until `dry_run`, `review_required`, `apply_instruction`, and `approved:true` are wired

## Good launch framing

> AKBP is not another chat memory. It is a local-first protocol for reviewed project knowledge: cited claims, source hashes, lifecycle history, dry-run writes, conformance checks, and portable bundles.

## Best public demo path

For a first-time reviewer, run these in order:

```bash
make demo
examples/akbp-bench/run.sh
examples/repo-memory-demo/run.sh
examples/session-start-harness/run.sh
examples/memory-ci/run.sh
examples/multi-agent-consistency-demo/run.sh
examples/existing-memory-migration/run.sh
examples/read-only-adapter/run.sh
```

That path shows the protocol, the benchmark, the repo use case, inherited-repo intake, the CI gate, cross-agent consistency, reviewed migration from existing memory, and read-only adapter rollout.
