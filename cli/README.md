# AKBP CLI

Dependency-free reference CLI for AKBP Level 0/1.

## Usage

```bash
python3 cli/akbp.py init --path ./my-kb
python3 cli/akbp.py --path ./my-kb remember "This project uses Bun instead of npm" --type decision --evidence README.md
python3 cli/akbp.py --path ./my-kb query "Bun npm"
python3 cli/akbp.py --path ./my-kb crystallize transcript.md --apply
python3 cli/akbp.py --path ./my-kb lint
```

This implementation writes portable markdown and JSONL artifacts. It is intentionally small so other implementations can copy the behavior.
