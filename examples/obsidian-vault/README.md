# Obsidian Vault Example

This example is a small AKBP knowledge base that can also be opened as an Obsidian vault.

Use it to see the intended split:

- Obsidian reads the Markdown notes in `AKBP.md` and `wiki/`.
- AKBP stores agent-readable durable memory in `claims/`, `raw/sources/`, and `graph/`.
- Agents should write through AKBP dry-run and approval flows instead of silently editing memory.

Try it:

```bash
akbp --path examples/obsidian-vault conformance --level 2
akbp --path examples/obsidian-vault query "how should agents store memory in obsidian"
```
