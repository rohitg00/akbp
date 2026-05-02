.PHONY: test guard smoke install-smoke benchmark-score benchmark validate build clean

test:
	python3 -m unittest discover -s tests -p 'test_*.py' -v

guard:
	python3 tests/guard_public_refs.py

smoke:
	TMP=$$(mktemp -d); \
	python3 cli/akbp.py --path $$TMP/kb init; \
	python3 cli/akbp.py --path $$TMP/kb source add AKBP.md --type file; \
	python3 cli/akbp.py --path $$TMP/kb remember "AKBP smoke test claim" --evidence AKBP.md; \
	python3 cli/akbp.py --path $$TMP/kb conformance --level 2; \
	python3 cli/akbp.py --path $$TMP/kb index; \
	python3 cli/akbp.py --path $$TMP/kb search smoke

install-smoke:
	TMP=$$(mktemp -d); \
	python3 -m pip install . --target $$TMP/pkg >/tmp/akbp-install-smoke.log; \
	PYTHONPATH=$$TMP/pkg python3 -m akbp --path $$TMP/kb init; \
	PYTHONPATH=$$TMP/pkg python3 -c "import akbp, akbp_tool_server; print('install ok')"

benchmark-score:
	python3 benchmarks/run_benchmarks.py --score

benchmark:
	python3 benchmarks/run_benchmarks.py --akbp

validate: guard test smoke benchmark-score benchmark install-smoke

build:
	python3 -m build

clean:
	rm -rf build dist *.egg-info cli/*.egg-info
