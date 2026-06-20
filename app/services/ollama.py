import json
import logging
import os
import re
import time

import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "translategemma:27b")
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "120"))

VALIDATE_PROMPT_TEMPLATE = """You are a multilingual linguistics assistant and spelling checker.

Check whether the following text is correctly written in {lang_name}.
Consider spelling, grammar, diacritical marks, and natural usage.

IMPORTANT — diacritical marks are never optional:
- In Hungarian, á é í ó ö ő ú ü ű are completely different letters from a e i o u.
  Writing "u" when the correct letter is "ü", or "e" when it should be "é", is a spelling error.
  Treat any missing or substituted accent as an error, even if the word is otherwise recognisable.
- Apply the same strict rule for any language that uses diacritical marks.

Input text: "{text}"

Respond ONLY with a valid JSON object. No explanation, no markdown, no code fences.

The JSON must have exactly these fields:
{{
  "is_valid": <true if the text is correct, false if it contains any error>,
  "corrections": ["<corrected version>", "..."] or null
}}

Rules:
- If is_valid is true, corrections must be null
- If is_valid is false, provide 1 to 3 corrected versions of the full text in order of likelihood
- Corrections should be minimal — fix only the actual errors, preserve the user's intended meaning
- Return null for corrections if you are not confident about any correction"""

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

SYNONYMS_PROMPT_TEMPLATE = """You are a multilingual linguistics assistant.

Provide synonyms for the following {source_lang_name} word.

Source word: "{source_text}"
Translation ({target_lang_name}): "{target_text}"
Part of speech: {part_of_speech}

Respond ONLY with a valid JSON object. No explanation, no markdown, no code fences.

The JSON must have exactly these fields:
{{
  "synonyms": ["<synonym in {source_lang_name}>", "..."] or null
}}

Rules:
- Provide up to 4 synonyms in {source_lang_name} in the same form as the source word
- Do not include the source word itself as a synonym
- Return null if no confident synonyms exist"""


async def translate(text: str, source_lang_name: str, target_lang_name: str) -> tuple[dict, list[float]]:
    """Call Ollama to translate text and return enriched linguistic data with per-call timings in ms."""
    prompt = PROMPT_TEMPLATE.format(
        source_lang_name=source_lang_name,
        target_lang_name=target_lang_name,
        text=text,
    )

    logger.info(
        "ollama translate start model=%s text=%r src=%s tgt=%s timeout=%.0fs",
        OLLAMA_MODEL, text, source_lang_name, target_lang_name, OLLAMA_TIMEOUT,
    )
    try:
        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
            t0 = time.monotonic()
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                },
            )
            duration_ms = round((time.monotonic() - t0) * 1000, 2)
            response.raise_for_status()
    except (httpx.HTTPError, httpx.ConnectError) as e:
        logger.error("ollama translate failed after %.0fms: %s", (time.monotonic() - t0) * 1000, e)
        raise HTTPException(
            status_code=502,
            detail="Ollama service unavailable or returned an error",
        )

    logger.info("ollama translate done duration_ms=%.2f", duration_ms)
    raw_text = ""
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

        return result, [duration_ms]
    except (json.JSONDecodeError, KeyError) as e:
        logger.error("ollama translate parse error: %s | raw=%r", e, raw_text[:200])
        raise HTTPException(
            status_code=502,
            detail="Ollama returned invalid output",
        )


async def get_synonyms(
    source_text: str,
    target_text: str,
    part_of_speech: str | None,
    source_lang_name: str,
    target_lang_name: str,
) -> tuple[list[str] | None, list[float]]:
    """Call Ollama to get synonyms for a word, given its translation and part of speech."""
    prompt = SYNONYMS_PROMPT_TEMPLATE.format(
        source_lang_name=source_lang_name,
        target_lang_name=target_lang_name,
        source_text=source_text,
        target_text=target_text,
        part_of_speech=part_of_speech or "unknown",
    )

    logger.info(
        "ollama synonyms start model=%s word=%r pos=%s timeout=%.0fs",
        OLLAMA_MODEL, source_text, part_of_speech, OLLAMA_TIMEOUT,
    )
    try:
        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
            t0 = time.monotonic()
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                },
            )
            duration_ms = round((time.monotonic() - t0) * 1000, 2)
            response.raise_for_status()
    except (httpx.HTTPError, httpx.ConnectError) as e:
        logger.error("ollama synonyms failed after %.0fms: %s", (time.monotonic() - t0) * 1000, e)
        raise HTTPException(
            status_code=502,
            detail="Ollama service unavailable or returned an error",
        )

    logger.info("ollama synonyms done duration_ms=%.2f", duration_ms)
    raw_text = ""
    try:
        ollama_response = response.json()
        raw_text = ollama_response["response"]

        cleaned = re.sub(r"^```(?:json)?\s*", "", raw_text.strip())
        cleaned = re.sub(r"\s*```$", "", cleaned)

        result = json.loads(cleaned)

        synonyms = result.get("synonyms")
        if isinstance(synonyms, list):
            synonyms = [s for s in synonyms if s is not None] or None

        return synonyms, [duration_ms]
    except (json.JSONDecodeError, KeyError) as e:
        logger.error("ollama synonyms parse error: %s | raw=%r", e, raw_text[:200])
        raise HTTPException(
            status_code=502,
            detail="Ollama returned invalid output",
        )


async def validate(text: str, lang_name: str) -> tuple[dict, list[float]]:
    """Call Ollama to check whether text is correctly written and return corrections if not."""
    prompt = VALIDATE_PROMPT_TEMPLATE.format(lang_name=lang_name, text=text)

    try:
        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
            t0 = time.monotonic()
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                },
            )
            duration_ms = round((time.monotonic() - t0) * 1000, 2)
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

        cleaned = re.sub(r"^```(?:json)?\s*", "", raw_text.strip())
        cleaned = re.sub(r"\s*```$", "", cleaned)

        result = json.loads(cleaned)

        # Normalise corrections: filter null entries, collapse empty list to null
        corrections = result.get("corrections")
        if isinstance(corrections, list):
            result["corrections"] = [c for c in corrections if c is not None] or None

        return result, [duration_ms]
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Failed to parse Ollama response: {e}")
        raise HTTPException(
            status_code=502,
            detail="Ollama returned invalid output",
        )
