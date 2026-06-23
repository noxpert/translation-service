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
- POST to {OLLAMA_BASE_URL}/api/generate with stream: false, format: "json", and options: DECODE_OPTIONS (temperature 0, top_p 1, repeat_penalty 1.0) for deterministic structured output
- All three calls (translate, get_synonyms, validate) share the module-level DECODE_OPTIONS constant defined in app/services/ollama.py
- The model returns a 'response' field containing the JSON string; strip markdown code fences before JSON parsing (kept as defensive fallback even though format=json returns clean JSON)
- Supported local models: `translategemma:12b`, `translategemma:27b`, `qwen3.6:35b-a3b`
- Model is configured via `OLLAMA_MODEL` in `.env` (single source of truth); docker-compose fallback is `translategemma:27b`
- Timeout: 60 seconds

## Translate Endpoint — Ollama Call Pattern
The `/translate` endpoint makes one or two Ollama calls:
1. **translate** (always) — returns source_text, target_text, part_of_speech, root_source, root_target, notes
2. **synonyms** (optional) — called only when `root_source` is non-null (i.e. input was inflected/conjugated); takes source word, target word, and POS; returns synonyms list

`ollama_calls_ms` in the response is a `dict[str, float]` with keys `"translate"` and optionally `"synonyms"`, each holding the wall-clock duration in ms for that call.

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
- Run tests with coverage: make coverage
- Run live-Ollama integration/performance tests: make test-integration
  - Opt-in (gated by RUN_OLLAMA_INTEGRATION); the normal suite stays fully mocked and skips these
  - Lives in tests/integration/ (hits a real Ollama via /translate and /validate, Hungarian→English)
  - Warms the model with one untimed call per endpoint, then records inputs, outputs, and per-call
    Ollama timings to tests/integration/results/ (JSON + Markdown) for both passing and failing runs
  - Report filenames embed the model and a UTC timestamp (results_<model>_<UTC>.json/.md) so runs
    never overwrite each other
- Run the integration suite across several models: make test-integration-models MODELS="translategemma:12b qwen3.6:35b-a3b"
  - Defaults to all three supported models when MODELS is omitted (scripts/run_integration.sh)
- Compare 2-3 result files: make compare FILES="results/a.json results/b.json" (scripts/compare_runs.py)
  - Diffs pass/fail and per-case Ollama timings; use it for before/after a code change or model-vs-model
- View logs: make logs
- Never run pytest directly on the host; always use make test or docker compose run
- Lint (host): make lint — uses ruff (config in pyproject.toml)
- Type check (host): make typecheck — uses mypy (config in pyproject.toml)
- Install dev tools: pip install -r requirements-dev.txt

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

When adding, removing, or modifying any API endpoint or its request/response schema, also update
ai-docs/api-reference.md — it is the shareable API reference used for planning with AI assistants.
