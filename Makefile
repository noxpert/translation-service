.PHONY: build up down restart logs test test-short test-file shell shell-run db-shell clean help

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
	docker compose restart hungarian-service

## Tail service logs
logs:
	docker compose logs -f hungarian-service

## Run all tests inside the container (uses isolated DB)
test:
	docker compose run --rm \
		-e DATABASE_URL=sqlite:///./test.db \
		hungarian-service \
		pytest tests/ -v

## Run tests with short output
test-short:
	docker compose run --rm \
		-e DATABASE_URL=sqlite:///./test.db \
		hungarian-service \
		pytest tests/ -q

## Run a specific test file (usage: make test-file FILE=tests/test_words.py)
test-file:
	docker compose run --rm \
		-e DATABASE_URL=sqlite:///./test.db \
		hungarian-service \
		pytest $(FILE) -v

## Open a shell inside the running container
shell:
	docker compose exec hungarian-service /bin/bash

## Open a shell in a fresh container (service need not be running)
shell-run:
	docker compose run --rm hungarian-service /bin/bash

## Open SQLite shell on the host database
db-shell:
	sqlite3 data/hungarian.db

## Remove the Docker image and rebuild from scratch
clean:
	docker compose down --rmi local
	docker compose build --no-cache

## Show this help
help:
	@grep -E '^##' Makefile | sed 's/## //'
