# Summary

## Changes

-

## Verification

- [ ] `python3 -m unittest discover -s tests -p 'test_*.py' -v`
- [ ] Public docs contain no private/local maintenance tool names
- [ ] Schema IDs resolve to public raw GitHub URLs
- [ ] Markdown docs start with `# `

## Protocol impact

- [ ] No protocol impact
- [ ] Protocol clarification
- [ ] Protocol addition
- [ ] Breaking protocol change, dated spec update included

## Adapter checklist

Complete this section when adding or changing an adapter.

- [ ] Adapter docs point to `docs/AGENT_FLOW.md`
- [ ] Required files are present: `README.md`, `instructions.md`, `config.example.json`, `session-start.md`, `session-end.md`, `privacy.md`
- [ ] Examples use public-safe names and no private paths, tokens, screenshots, cookies, logs, or user-specific config
- [ ] Write-capable examples default to dry-run or explain approval requirements
- [ ] Durable output remains AKBP-compatible: wiki pages, JSONL claims, graph records, sources, audit events, and context packs
- [ ] Adapter does not introduce a new memory format as source of truth

## AI assistance disclosure

Describe whether AI assistance materially contributed to this PR.
