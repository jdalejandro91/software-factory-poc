.PHONY: run test lint up down logs

run:
	./scripts/run_dev.sh

test:
	./scripts/test_all.sh

lint:
	python3 -m ruff check .

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f