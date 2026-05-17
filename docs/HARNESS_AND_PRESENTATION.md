# Harness and tool-output presentation

A 2026 agent-harness study evaluated how retrieval strategy choice interacts
with agent architecture and tool-output presentation on a sample drawn from
the LongMemEval suite. Two findings matter for AKBP:

1. Plain text-grep retrieval over the underlying corpus competed favorably
   with vector retrieval on that sample.
2. Whether a tool returned results inline or wrote them to a separate file the
   model could read changed end-to-end scores even when the retrieved evidence
   was identical.

Reference: Sen, Kasturi, Lumer, Gulati, Subbiah. *Is Grep All You Need? How
Agent Harnesses Reshape Agentic Search.* arXiv:2605.15184.

AKBP does not need to take a partisan position on grep vs vector vs hybrid
retrieval. It does need to take a position on how the protocol exposes
retrieval to the harness, because the study suggests presentation is part of
the contract, not a UI concern.

## Position

AKBP keeps retrieval surface simple and harness-agnostic:

- `akbp.search` and `akbp.context` always use the indexed SQLite FTS5 backend
  when an index is present, and an unindexed keyword fallback otherwise. The
  backend is reported on every response so adapters know which path ran.
- Both methods accept an explicit `output_mode` parameter. `inline` is the
  default and returns results in the response body. `file` writes a
  newline-delimited JSON artifact to a caller-supplied (or environment-defined)
  directory and returns a compact envelope with the artifact path, sha256,
  byte size, and line count.
- The artifact format is deliberately grep-friendly: the first line carries
  metadata, each remaining line is one result or context item. A harness can
  `rg`, `jq`, or stream the file without re-parsing a nested response envelope
  or paying the prompt cost of inlining the full payload.
- The response envelope echoes `output_mode` so adapters can confirm which
  shape they received, and the schemas (`#/$defs/search_result`,
  `#/$defs/search_result_file`, `#/$defs/context_result`,
  `#/$defs/context_result_file`) document both shapes explicitly.

The protocol intentionally does not pick a winner between grep, BM25, vector,
or hybrid retrieval. It does require that whichever backend an adapter or
companion store uses, results are cited, lifecycle-aware, and presented
through one of the two declared modes.

## What this changes for adapters

| Before | After |
|---|---|
| Adapters always inlined `results[]` or `items[]` into the prompt. | Adapters can request `output_mode: "file"` and load only the envelope, then use ripgrep, jq, or streaming reads against the artifact. |
| Tool-output presentation was an undocumented implementation detail. | Tool-output presentation is a documented capability with explicit schemas, benchmark coverage, and adapter prompt-contract guidance. |
| The retrieval discussion was framed as "FTS5 today, vector roadmap". | The retrieval discussion is framed as "FTS5 today, vector roadmap, and explicit presentation contract so harnesses can carry grep-like workflows when that fits the task". |

## What this does not change

- Review-gated writes, source hashes, citation requirements, supersession,
  contradiction handling, audit log, and adapter readiness gates are
  unchanged.
- The benchmark fixtures still prefer cited recall and lifecycle correctness
  over raw scoreboard numbers.
- The protocol still avoids advertising itself as a memory product. AKBP is
  a substrate; how a harness presents AKBP results to a model is now part of
  the negotiated contract.

## Open work

- Run a LongMemEval-shaped slice against AKBP FTS5 alongside any sibling
  hybrid memory store, and publish the inline-versus-file presentation
  comparison so the benchmark answers the paper's question for this stack
  with measured numbers instead of restated assumptions.
- Track noise-robustness curves (irrelevant turns or unrelated claims added
  to the working set) so the protocol position survives the same stress
  tests the paper applied to harnesses.
- Continue rejecting any presentation shortcut that bypasses citation or
  lifecycle metadata. File mode must not become a way to ship uncited
  evidence to the model.

This document is the AKBP-internal response to the paper. It is not a claim
that file mode is universally better than inline mode. It is a claim that the
choice is now a first-class part of the AKBP tool contract and benchmark
surface.
