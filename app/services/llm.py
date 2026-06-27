"""LLM backend dispatcher.

Selects the backend based on the LLM_BACKEND environment variable:
  LLM_BACKEND=ollama  (default) — uses app.services.ollama
  LLM_BACKEND=claude            — uses app.services.claude_service

The three async functions (translate, get_synonyms, validate) call through the
selected backend module rather than holding direct function references, so that
unittest.mock.patch("app.services.ollama.*") patches continue to work in the
mocked unit suite without any changes to those tests.
"""

import os

LLM_BACKEND: str = os.getenv("LLM_BACKEND", "ollama").lower()

if LLM_BACKEND == "claude":
    import app.services.claude_service as _backend
    MODEL_NAME: str = _backend.ANTHROPIC_MODEL
    BASE_URL: str = "https://api.anthropic.com"
else:
    import app.services.ollama as _backend  # type: ignore[assignment]
    MODEL_NAME = _backend.OLLAMA_MODEL
    BASE_URL = _backend.OLLAMA_BASE_URL


async def translate(*args, **kwargs):
    return await _backend.translate(*args, **kwargs)


async def get_synonyms(*args, **kwargs):
    return await _backend.get_synonyms(*args, **kwargs)


async def validate(*args, **kwargs):
    return await _backend.validate(*args, **kwargs)
