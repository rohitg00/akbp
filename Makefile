.PHONY: test guard smoke build clean

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

build:
	python3 -m build

clean:
	rm -rf build dist *.egg-info cli/*.egg-info
