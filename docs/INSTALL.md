# Install

AKBP currently ships as a small dependency-free Python reference implementation.

## Requirements

- Python 3.9 or newer
- `pip` for local installation

No runtime package dependencies are required.

## Run from source

For a complete first-run path, read `docs/GETTING_STARTED.md` before choosing an install mode.

```bash
git clone https://github.com/rohitg00/akbp.git
cd akbp
python3 cli/akbp.py --help
```

Create a knowledge base:

```bash
python3 cli/akbp.py --path ./my-kb init
```

## Install locally

From the repository root:

```bash
python3 -m pip install .
```

Then use the installed command:

```bash
akbp --help
akbp --path ./my-kb init
```

## Isolated local install smoke test

This installs AKBP into a temporary target directory without modifying your global Python environment:

```bash
TMP=$(mktemp -d)
python3 -m pip install . --target "$TMP/pkg"
PYTHONPATH="$TMP/pkg" python3 -m akbp --path "$TMP/kb" init
PYTHONPATH="$TMP/pkg" python3 -c "import akbp, akbp_tool_server; print('ok')"
PATH="$TMP/pkg/bin:$PATH" PYTHONPATH="$TMP/pkg" akbp --path "$TMP/kb-cli" init
PATH="$TMP/pkg/bin:$PATH" PYTHONPATH="$TMP/pkg" akbp --help
printf '%s\n' \
  '{"id":"caps","method":"akbp.capabilities"}' \
  '{"id":"bad","method":"akbp.search","params":{"query":"release","limit":0}}' \
  | PYTHONPATH="$TMP/pkg" python3 -m akbp_tool_server
printf '%s\n' '{"id":"caps","method":"akbp.capabilities"}' \
  | PATH="$TMP/pkg/bin:$PATH" PYTHONPATH="$TMP/pkg" akbp-tool-server
```

The installed smoke test should prove both importable modules and console scripts work. The tool-server checks should show advertised method-schema features, include `akbp.import_apply` in capabilities, and return schema-backed `invalid_params` details for the bad request.

## Build a source distribution and wheel

Install the build frontend if your Python environment does not already have it:

```bash
python3 -m pip install build
```

Build artifacts:

```bash
python3 -m build
```

Generated files appear in `dist/`.

The source distribution includes the protocol docs, schemas, examples, adapters, and benchmark fixtures via `MANIFEST.in`. The installed console scripts remain the dependency-free reference CLI and JSONL tool server.

## Console commands

The package installs two console commands:

```text
akbp              reference CLI
akbp-tool-server  JSONL local tool server
```

## Verify

Run the full local validation set before publishing or tagging a release:

```bash
make validate
```

`make validate` runs the public-reference guard, unit and conformance tests, CLI smoke flow, runnable public examples, retrieval benchmarks, and install smoke flow.

For faster local iteration, run individual targets such as `make test`, `make guard`, or `make smoke`.
