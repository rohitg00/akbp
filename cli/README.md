# AKBP CLI

Dependency-free reference CLI for AKBP Level 0/1.

## Usage

```bash
python3 cli/akbp.py init --path ./my-kb
python3 cli/akbp.py --path ./my-kb remember "This project uses Bun instead of npm" --type decision --evidence README.md
python3 cli/akbp.py --path ./my-kb query "Bun npm"
python3 cli/akbp.py --path ./my-kb context "continue the package manager migration"
python3 cli/akbp.py --path ./my-kb cite claim_123
python3 cli/akbp.py --path ./my-kb supersede claim_123 "Use the stdlib CLI until package metadata exists" --type decision --evidence cli/akbp.py
python3 cli/akbp.py --path ./my-kb conformance --level 1
python3 cli/akbp.py --path ./my-kb crystallize transcript.md --apply
python3 cli/akbp.py --path ./my-kb lint
```

This implementation writes portable markdown and JSONL artifacts. It is intentionally small so other implementations can copy the behavior.

## Context packs

`akbp context` returns a protocol-shaped context pack for agents. It is the CLI equivalent of the planned `akbp.get_context` tool protocol tool.

## Conformance

`akbp conformance --level 0` checks the minimal file convention: `AKBP.md`, `akbp.json`, portable artifact paths, and required card capabilities.

`akbp conformance --level 1` also validates structured claims: required fields, unique IDs, lifecycle status, confidence range, and evidence shape.
