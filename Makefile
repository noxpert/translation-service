.PHONY: build up down restart logs test test-short test-file coverage lint typecheck shell shell-run db-shell clean help

## Build the Docker image
build:
	docker compose build

## Start the service in the background
up:
	mkdir -p data
	docker compose up -d

## Stop the service
down:
	docker compose down

## Restart the service
restart:
	docker compose restart translation-service

## Tail service logs
logs:
	docker compose logs -f translation-service

## Run all tests inside the container (uses isolated in-memory DB)
test:
	docker compose run --rm \
		-e DATABASE_URL=sqlite:// \
		-e PYTHONPATH=/app \
		translation-service \
		pytest tests/ -v

## Run tests with short output
test-short:
	docker compose run --rm \
		-e DATABASE_URL=sqlite:// \
		-e PYTHONPATH=/app \
		translation-service \
		pytest tests/ -q

## Run live-Ollama integration/performance tests (needs a running Ollama); writes reports to tests/integration/results/
test-integration:
	mkdir -p tests/integration/results
	docker compose run --rm \
		-e DATABASE_URL=sqlite:// \
		-e PYTHONPATH=/app \
		-e RUN_OLLAMA_INTEGRATION=1 \
		-e INTEGRATION_RESULTS_DIR=/results \
		-v "$(CURDIR)/tests/integration/results:/results" \
		translation-service \
		pytest tests/integration -v -s

## Run integration tests against Claude Sonnet (needs ANTHROPIC_API_KEY exported in the shell)
test-integration-claude:
	mkdir -p tests/integration/results
	docker compose run --rm \
		-e DATABASE_URL=sqlite:// \
		-e PYTHONPATH=/app \
		-e RUN_OLLAMA_INTEGRATION=1 \
		-e LLM_BACKEND=claude \
		-e ANTHROPIC_API_KEY \
		-e ANTHROPIC_MODEL \
		-e INTEGRATION_RESULTS_DIR=/results \
		-v "$(CURDIR)/tests/integration/results:/results" \
		translation-service \
		pytest tests/integration -v -s

## Run the integration suite for several models (usage: make test-integration-models MODELS="translategemma:12b qwen3.6:35b-a3b"; defaults to all three)
test-integration-models:
	scripts/run_integration.sh $(MODELS)

## Compare 2-3 integration result files (usage: make compare FILES="tests/integration/results/a.json tests/integration/results/b.json")
compare:
	python3 scripts/compare_runs.py $(FILES)

## Run a specific test file (usage: make test-file FILE=tests/test_words.py)
test-file:
	docker compose run --rm \
		-e DATABASE_URL=sqlite:// \
		-e PYTHONPATH=/app \
		translation-service \
		pytest $(FILE) -v

## Run tests with coverage report (requires make build first if code changed)
coverage:
	docker compose run --rm \
		-e DATABASE_URL=sqlite:// \
		-e PYTHONPATH=/app \
		-e COVERAGE_FILE=/tmp/.coverage \
		translation-service \
		pytest tests/ -v --cov=app --cov-report=term-missing

## Check code style and imports (requires: pip install -r requirements-dev.txt)
lint:
	ruff check app/ tests/

## Run static type checking (requires: pip install -r requirements-dev.txt)
typecheck:
	mypy app/

## Open a shell inside the running container
shell:
	docker compose exec translation-service /bin/bash

## Open a shell in a fresh container (service need not be running)
shell-run:
	docker compose run --rm translation-service /bin/bash

## Open SQLite shell on the host database
db-shell:
	sqlite3 data/translations.db

## Remove the Docker image and rebuild from scratch
clean:
	docker compose down --rmi local
	docker compose build --no-cache

## Show this help
help:
	@grep -E '^##' Makefile | sed 's/## //'
