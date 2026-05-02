# Install

AKBP currently ships as a small dependency-free Python reference implementation.

## Requirements

- Python 3.9 or newer
- `pip` for local installation

No runtime package dependencies are required.

## Run from source

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
```

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

`make validate` runs the public-reference guard, unit and conformance tests, CLI smoke flow, retrieval benchmarks, and install smoke flow.

For faster local iteration, run individual targets such as `make test`, `make guard`, or `make smoke`.
