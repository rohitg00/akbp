.PHONY: test guard smoke install-smoke demo examples benchmark-score benchmark validate build clean

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
	PYTHONPATH=$$TMP/pkg python3 -c "import akbp, akbp_tool_server; print('install ok')"; \
	PATH=$$TMP/pkg/bin:$$PATH PYTHONPATH=$$TMP/pkg akbp --path $$TMP/kb-cli init; \
	PATH=$$TMP/pkg/bin:$$PATH PYTHONPATH=$$TMP/pkg akbp --help >/dev/null; \
	printf '%s\n' '{"id":"caps","method":"akbp.capabilities"}' '{"id":"bad","method":"akbp.search","params":{"query":"release","limit":0}}' | PYTHONPATH=$$TMP/pkg python3 -m akbp_tool_server | python3 -c "import json,sys; rows=[json.loads(line) for line in sys.stdin if line.strip()]; assert rows[0]['result']['features']['method_param_schemas']; assert 'akbp.import_apply' in rows[0]['result']['methods']; assert rows[1]['error']['code'] == 'invalid_params'; assert 'limit must be between 1 and 100' in rows[1]['error']['details']['type_errors']; print('tool server module install ok')"; \
	printf '%s\n' '{"id":"caps","method":"akbp.capabilities"}' | PATH=$$TMP/pkg/bin:$$PATH PYTHONPATH=$$TMP/pkg akbp-tool-server | python3 -c "import json,sys; row=json.loads(sys.stdin.readline()); assert row['result']['features']['method_param_schemas']; assert 'akbp.import_apply' in row['result']['methods']; print('tool server console install ok')"

demo:
	./examples/quickstart-demo/run.sh

examples:
	./examples/akbp-bench/run.sh
	./examples/repo-memory-demo/run.sh
	./examples/memory-ci/run.sh
	./examples/jsonl-quickstart/run.sh
	./examples/tool-server-approval-flow/run.sh
	./examples/tool-error-handling/run.sh
	./examples/session-start-harness/run.sh
	./examples/structured-output-harness/run.sh
	./examples/adapter-lifecycle/run.sh
	./examples/multi-agent-consistency-demo/run.sh
	./examples/portable-bundle/run.sh
	./examples/existing-memory-migration/run.sh
	./examples/source-intake/run.sh
	./examples/read-only-adapter/run.sh
	./examples/stdio-client-config/run.sh

benchmark-score:
	python3 benchmarks/run_benchmarks.py --score

benchmark:
	python3 benchmarks/run_benchmarks.py --akbp

validate: guard test smoke examples benchmark-score benchmark install-smoke

build:
	python3 -m build

clean:
	rm -rf build dist *.egg-info cli/*.egg-info
