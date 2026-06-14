import json
import logging
import os
import re

import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "translategemma:27b")

PROMPT_TEMPLATE = """You are a multilingual linguistics assistant.

Translate the following text from {source_lang_name} to {target_lang_name}.

Input text: "{text}"

Respond ONLY with a valid JSON object. No explanation, no markdown, no code fences.

The JSON must have exactly these fields:
{{
  "source_text": "<the original input text>",
  "target_text": "<the translation>",
  "part_of_speech": "<one of: noun, verb, adj, adv, other, or null if a phrase>",
  "root_source": "<root/lemma form in source language, or null if input is already the root>",
  "root_target": "<translation of the root form, or null>",
  "notes": "<brief linguistic notes about the translation, or null>"
}}

Rules:
- part_of_speech should be null if the input is a phrase or clause
- root_source: the dictionary/lemma form of the input word — only set this if the input is inflected or conjugated, otherwise null.
  For Hungarian verbs the lemma is always the infinitive ending in -ni/-ani/-eni (e.g. sietek → sietni, olvasom → olvasni, futok → futni, ment → menni, van → lenni).
  For Hungarian nouns/adjectives remove case suffixes to get the base form (e.g. autóba → autó, házban → ház).
  For nouns derived from verbs, use the noun as the root, not the underlying verb.
- root_target: the {target_lang_name} translation of root_source, or null if root_source is null
- notes: mention conjugation pattern, suffix meaning, or alternate meanings if relevant
- Return null for any field you are not confident about rather than guessing"""


async def translate(text: str, source_lang_name: str, target_lang_name: str) -> dict:
    """Call Ollama to translate text and return enriched linguistic data."""
    prompt = PROMPT_TEMPLATE.format(
        source_lang_name=source_lang_name,
        target_lang_name=target_lang_name,
        text=text,
    )

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                },
            )
            response.raise_for_status()
    except (httpx.HTTPError, httpx.ConnectError) as e:
        logger.error(f"Ollama request failed: {e}")
        raise HTTPException(
            status_code=502,
            detail="Ollama service unavailable or returned an error",
        )

    try:
        ollama_response = response.json()
        raw_text = ollama_response["response"]

        # Strip markdown code fences if present
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw_text.strip())
        cleaned = re.sub(r"\s*```$", "", cleaned)

        result = json.loads(cleaned)

        # If the model returned the input word as its own root, the root adds no information
        root_source = result.get("root_source") or ""
        if root_source.strip().lower() == text.strip().lower():
            result["root_source"] = None
            result["root_target"] = None

        return result
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Failed to parse Ollama response: {e}")
        raise HTTPException(
            status_code=502,
            detail="Ollama returned invalid output",
        )
