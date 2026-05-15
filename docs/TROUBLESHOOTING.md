# Troubleshooting

Use this when the quickstart demo or a local adapter integration fails.

## `python3` is missing or too old

AKBP is tested with the system `python3` available in CI and local smoke flows. If your shell cannot find Python:

```bash
python3 --version
```

Install Python 3, then rerun:

```bash
make validate
```

## akbp command is not found

The installed console script is available after:

```bash
python3 -m pip install .
```

For repository-local development, use:

```bash
python3 cli/akbp.py --help
```

The JSONL tool server console script is named:

```bash
akbp-tool-server
```

The module forms are:

```bash
python3 -m akbp --help
python3 -m akbp_tool_server
```

## A write returns `approval_required`

This is expected. Write-capable JSONL methods are review-gated.

Preview first:

```json
{"id":"1","method":"akbp.remember","path":".","dry_run":true,"params":{"text":"Decision to keep releases small"}}
```

Apply only after review:

```json
{"id":"2","method":"akbp.remember","path":".","approved":true,"params":{"text":"Decision to keep releases small"}}
```

Do not branch on free-form error messages. Branch on `error.code`.

## `source verify` reports `changed` or `missing`

A registered source no longer matches the saved hash, or the file is gone.

Run:

```bash
python3 cli/akbp.py --path ./my-kb source verify
```

Then review the result buckets:

- `verified`: source still matches.
- `changed`: source exists but its hash changed.
- `missing`: source file cannot be found, or a requested source id is not registered.
- `unchecked`: source type cannot be hash-checked locally.

For changed sources, add a new source record or update the durable claim only after reviewing the new evidence.

## `export-check` rejects a bundle

Inspect the reported issues before import/apply. Common causes:

- Unknown `source_...` evidence ids.
- Claim evidence that points at paths or notes instead of registered source ids.
- Secret-like values in JSONL objects.
- Missing manifest fields.
- Artifact hashes that do not match the exported files.

Use `import-check` before `import-apply` when consuming external JSONL:

```bash
python3 cli/akbp.py --path ./my-kb import-check bundle.jsonl --fail-on-rejected
```

## Search returns no results

Build or refresh the local index:

```bash
python3 cli/akbp.py --path ./my-kb index --incremental
```

AKBP search uses SQLite FTS5. Punctuation-only tokens are ignored. Useful examples:

```bash
python3 cli/akbp.py --path ./my-kb search "release checklist"
python3 cli/akbp.py --path ./my-kb search "rollback AND release"
python3 cli/akbp.py --path ./my-kb search "deploy*"
```

## Validate before publishing an adapter

Run:

```bash
make validate
```

Then use:

- `docs/ADAPTER_REVIEW_CHECKLIST.md`
- `examples/tool-server-approval-flow/README.md`
- `examples/tool-error-handling/README.md`
- `examples/quickstart-demo/README.md`
