# Language Translation Service

## Project Purpose
A local-first REST API built with FastAPI and SQLite. It provides multilingual
translation via a local Ollama LLM and stores words and phrases for language study.
Intended to serve multiple small language-learning apps.

## Tech Stack
- Python 3.12, FastAPI, SQLAlchemy (ORM), Pydantic v2
- SQLite (file at /data/translations.db in container, ./data/translations.db on host)
- Ollama for LLM inference (runs on host, not in container)
- Docker + docker-compose for containerization
- pytest for tests (always run inside container via `make test`)

## Key Conventions
- All ORM models inherit from Base in app/database.py
- All Pydantic schemas use ConfigDict(from_attributes=True)
- Routers are thin; business logic lives in app/services/word_service.py
- Language codes use ISO 639-1 ('en', 'hu')
- Part of speech codes: noun, verb, adj, adv, other
- Unknown POS values are silently normalized to 'other' on write
- Cascade deletes are used; no soft deletes
- No unique constraint on word_translations or phrase_translations (multiple translations per language allowed)
- SQLite foreign key enforcement enabled via PRAGMA foreign_keys=ON on every connection

## Ollama Integration (Critical)
- TranslateGemma requires a SINGLE USER MESSAGE — no system role in the request
- POST to {OLLAMA_BASE_URL}/api/generate with stream: false
- The model returns a 'response' field containing the JSON string
- Always strip markdown code fences before JSON parsing
- Default model: translategemma:12b
- Timeout: 60 seconds

## Database
- DATABASE_URL env var controls connection (four slashes for absolute SQLite path)
- Tests use in-memory SQLite; never use the host database file in tests
- init_db() runs on startup and is idempotent (checks for existing seed data)
- No Alembic yet; schema changes require manual migration

## CI/CD
- GitHub Actions workflow at .github/workflows/ci.yml
- Runs on every PR to main and every push to main
- Builds the Docker image (with layer caching) then runs the full test suite
- Branch protection on main requires CI to pass before merge

## Running and Testing
- Start: make up
- Run tests: make test
- View logs: make logs
- Never run pytest directly on the host; always use make test or docker compose run

## File Layout
- app/models/       — SQLAlchemy ORM models
- app/schemas/      — Pydantic request/response models
- app/routers/      — FastAPI route handlers (thin)
- app/services/     — Business logic (word_service.py, ollama.py)
- app/db/init_db.py — Table creation and seed data
- tests/            — pytest tests; conftest.py sets up in-memory DB and TestClient

## Keeping Docs in Sync
When changing architecture, conventions, endpoints, or test patterns, update both this file
and .github/copilot-instructions.md — they serve different AI assistants but must stay consistent.
