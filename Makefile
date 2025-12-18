.PHONY: run test lint

run:
	./scripts/run_dev.sh

test:
	./scripts/test_all.sh

lint:
	python3 -m ruff check .
