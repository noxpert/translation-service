# Language Translation Service

A local-first REST API for translation and vocabulary management, powered by a local Ollama LLM and backed by SQLite.

My primary use case is for English <-> Hungarian translations, but it need not be limited to that.

## Prerequisites

- Docker Desktop (or Docker + Docker Compose)
- Ollama running locally with `translategemma:12b` (or another translation model)

## Quick Start

```bash
make build
make up
curl http://localhost:8001/
```

## Configuration

Copy `.env.example` to `.env` and adjust as needed:

```
DATABASE_URL=sqlite:////data/translations.db
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=translategemma:12b
```

Note the four slashes in the SQLite URL — three is relative, four is the absolute
path `/data/translations.db` inside the container.

## Running

| Command | Description |
|---------|-------------|
| `make build` | Build the Docker image |
| `make up` | Start the service (port 8001) |
| `make down` | Stop the service |
| `make restart` | Restart the service |
| `make logs` | Tail service logs |
| `make test` | Run all tests in the container |
| `make test-short` | Run all tests with compact output |
| `make test-file FILE=tests/test_translate.py` | Run a specific test file |
| `make shell` | Shell into the running container |
| `make shell-run` | Shell into a fresh container (service need not be running) |
| `make db-shell` | Open SQLite CLI on the host database |
| `make clean` | Remove the Docker image and rebuild from scratch |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Health check |
| POST | `/translate` | Translate text via Ollama |
| GET | `/languages` | List all languages |
| GET | `/parts-of-speech` | List all parts of speech |
| POST | `/words` | Save a word and its translations |
| PATCH | `/words/{id}` | Update a word and/or its translations |
| DELETE | `/words/{id}` | Delete a word and cascade its translations |
| POST | `/phrases` | Save a phrase and its translations |
| PATCH | `/phrases/{id}` | Update a phrase and/or its translations |
| DELETE | `/phrases/{id}` | Delete a phrase and cascade its translations |

## Database

The SQLite database lives at `./data/translations.db` on your host machine, mounted
into the container at `/data/translations.db`. Tables and seed data are created
automatically on first startup.

To back up: copy `./data/translations.db` to your preferred cloud sync folder.

## Ollama Model Note

The default model is `translategemma:12b`. This model requires a single user message
with no system role in the prompt. Do not add a system prompt to the Ollama request.

Swap to `translategemma:27b` in your `.env` for better quality at the cost of more memory.

## Adding a New Source App

Every word and phrase can be tagged with a `source_name` identifying which app
created it. Sources are created automatically on first use — just include
`"source_name": "my-app"` in your POST body and the service will create the
source record if it doesn't already exist. No pre-registration needed.
