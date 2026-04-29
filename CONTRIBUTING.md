# Contributing to AKBP

AKBP is a protocol-first project. Contributions should improve interoperability, clarity, safety, conformance, or reference implementations.

## Development setup

Requirements:

- Python 3.10 or newer
- Git

Run tests:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

## Contribution rules

- Keep public docs clear and implementation-neutral.
- Do not add unresolved domains or placeholder production URLs.
- Do not mention private/local maintenance tools in public docs, commit messages, issues, or pull requests.
- Protocol changes need examples and tests.
- Schema IDs must resolve to public raw GitHub URLs until a project website exists.
- Markdown docs should start with a level-one heading.

## Commit style

Use concise conventional-style commits:

```text
feat: add knowledge base card adoption path
fix: use resolvable schema ids
docs: clarify conformance levels
test: add schema validation coverage
```

## Protocol changes

Large protocol changes should start as a proposal in `proposals/`.

A proposal should include:

- problem
- proposed change
- alternatives considered
- compatibility impact
- security/privacy impact
- reference implementation plan
- conformance tests required

## AI assistance disclosure

If AI assistance materially contributed to a public issue, pull request, or proposal, disclose that plainly in the relevant public thread.
