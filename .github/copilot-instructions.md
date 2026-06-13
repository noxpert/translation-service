# Hungarian Language Service — Copilot Instructions

## What This Project Is
A FastAPI REST API that translates Hungarian/English text using a local Ollama LLM
and stores words and phrases in SQLite for language study. Containerized with Docker.

## Language and Frameworks
- Python 3.12
- FastAPI with async route handlers
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
- SQLite file at /data/hungarian.db (container) or ./data/hungarian.db (host)
- Four-slash SQLite URL for absolute path: sqlite:////data/hungarian.db
- All models have: id (PK autoincrement), created_at (DateTime, default utcnow)
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

## Testing
- Tests always run inside Docker: make test
- conftest.py provides an in-memory SQLite DB and overrides get_db
- Seed languages and parts_of_speech in conftest fixtures
- Mock app.services.ollama.translate in translate tests

## Common Patterns

### Dependency injection
```python
@router.get("/words")
async def list_words(db: Session = Depends(get_db)):
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
