# Language Translation Service — Copilot Instructions

## What This Project Is
A FastAPI REST API that translates text between languages using a local Ollama LLM
and stores words and phrases in SQLite for language study. Containerized with Docker.

## Language and Frameworks
- Python 3.12
- FastAPI — route handlers are sync by default; only `translate` is `async` (Ollama uses AsyncClient)
- SQLAlchemy ORM (not Core); models in app/models/
- Pydantic v2 schemas in app/schemas/ with ConfigDict(from_attributes=True)
- pytest for tests

## Architecture Rules
- Routers (app/routers/) handle HTTP only — no DB queries, no Ollama calls directly
- Business logic belongs in app/services/word_service.py
- Ollama HTTP calls belong in app/services/ollama.py
- get_db() from app/database.py is the FastAPI dependency for DB sessions
- SQLite foreign key enforcement is enabled via PRAGMA foreign_keys=ON

## Database Conventions
- SQLite file at /data/translations.db (container) or ./data/translations.db (host)
- Four-slash SQLite URL for absolute path: sqlite:////data/translations.db
- All models have: id (PK autoincrement), created_at (DateTime, default `datetime.now(timezone.utc)`)
- Cascade deletes on word_translations and phrase_translations
- No soft deletes; no unique constraint on translation rows

## Part of Speech Handling
- Valid codes: noun, verb, adj, adv, other
- On write: validate against parts_of_speech table; fall back to 'other' if unknown
- On translate response: same normalization, but nothing is written to DB

## Ollama Integration
- CRITICAL: TranslateGemma uses a single user message — never add a system role
- POST /api/generate with stream: false
- Parse the 'response' field from the result; strip any ```json fences
- Raise HTTPException(502) on any failure

## CI/CD
- GitHub Actions at .github/workflows/ci.yml — triggers on PRs to main and pushes to main
- `lint` job: runs ruff and mypy directly on the runner (no Docker)
- `test` job: builds the Docker image with GHA layer caching, then runs `pytest tests/ -v` inside the container
- Branch protection on main requires CI to pass before merge

## Linting and Type Checking
- ruff: style + import sorting (`make lint`); config in pyproject.toml
- mypy: static type checking (`make typecheck`); config in pyproject.toml
- Router functions are excluded from `disallow_untyped_defs` — FastAPI types via `response_model`
- Dev tools: `pip install -r requirements-dev.txt`

## Testing
- Tests always run inside Docker: make test
- Coverage report: make coverage (uses pytest-cov)
- conftest.py provides an in-memory SQLite DB and overrides get_db
- Seed languages and parts_of_speech in conftest fixtures
- Mock app.services.ollama.translate in translate tests

## Common Patterns

### Translate endpoint
```python
@router.post("/translate", response_model=TranslateResponse)
async def translate_text(body: TranslateRequest, db: Session = Depends(get_db)):
    ...
```
The request body uses `TranslateRequest` (fields: `text`, `source_lang`, `target_lang`).

### Dependency injection
```python
@router.get("/languages")
def get_languages(db: Session = Depends(get_db)):
    ...
```

### POS resolution (always use this pattern)
```python
pos = resolve_part_of_speech(db, code)  # returns 'other' row if unknown
```

### Language resolution (raises 400 if not found)
```python
lang = resolve_language(db, code)
```

## Keeping Docs in Sync
When changing architecture, conventions, endpoints, or test patterns, update both this file
and CLAUDE.md — they serve different AI assistants but must stay consistent.

When adding, removing, or modifying any API endpoint or its request/response schema, also update
ai-docs/api-reference.md — it is the shareable API reference used for planning with AI assistants.
