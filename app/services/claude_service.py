import json
import logging
import os
import re
import time

import anthropic
from fastapi import HTTPException

from app.services.ollama import (
    PROMPT_TEMPLATE,
    SYNONYMS_PROMPT_TEMPLATE,
    VALIDATE_PROMPT_TEMPLATE,
)

logger = logging.getLogger(__name__)

ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

# Client is instantiated at module load (only imported when LLM_BACKEND=claude).
# anthropic.AsyncAnthropic reads ANTHROPIC_API_KEY from the environment.
_client = anthropic.AsyncAnthropic()


async def _call(prompt: str) -> tuple[str, float]:
    t0 = time.monotonic()
    try:
        response = await _client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=1024,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        duration_ms = round((time.monotonic() - t0) * 1000, 2)
        return response.content[0].text, duration_ms
    except anthropic.APIError as e:
        logger.error("Claude API error: %s", e)
        raise HTTPException(status_code=502, detail="Claude API unavailable or returned an error")


def _parse_json(raw_text: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw_text.strip())
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return json.loads(cleaned)


async def translate(text: str, source_lang_name: str, target_lang_name: str) -> tuple[dict, list[float]]:
    prompt = PROMPT_TEMPLATE.format(
        source_lang_name=source_lang_name,
        target_lang_name=target_lang_name,
        text=text,
    )
    logger.info("claude translate start model=%s text=%r", ANTHROPIC_MODEL, text)
    raw_text, duration_ms = await _call(prompt)
    logger.info("claude translate done duration_ms=%.2f", duration_ms)
    try:
        result = _parse_json(raw_text)
        root_source = result.get("root_source") or ""
        if root_source.strip().lower() == text.strip().lower():
            result["root_source"] = None
            result["root_target"] = None
        return result, [duration_ms]
    except (json.JSONDecodeError, KeyError) as e:
        logger.error("claude translate parse error: %s | raw=%r", e, raw_text[:200])
        raise HTTPException(status_code=502, detail="Claude returned invalid output")


async def get_synonyms(
    source_text: str,
    target_text: str,
    part_of_speech: str | None,
    source_lang_name: str,
    target_lang_name: str,
) -> tuple[list[str] | None, list[float]]:
    prompt = SYNONYMS_PROMPT_TEMPLATE.format(
        source_lang_name=source_lang_name,
        target_lang_name=target_lang_name,
        source_text=source_text,
        target_text=target_text,
        part_of_speech=part_of_speech or "unknown",
    )
    logger.info("claude synonyms start model=%s word=%r", ANTHROPIC_MODEL, source_text)
    raw_text, duration_ms = await _call(prompt)
    logger.info("claude synonyms done duration_ms=%.2f", duration_ms)
    try:
        result = _parse_json(raw_text)
        synonyms = result.get("synonyms")
        if isinstance(synonyms, list):
            synonyms = [s for s in synonyms if s is not None] or None
        return synonyms, [duration_ms]
    except (json.JSONDecodeError, KeyError) as e:
        logger.error("claude synonyms parse error: %s | raw=%r", e, raw_text[:200])
        raise HTTPException(status_code=502, detail="Claude returned invalid output")


async def validate(text: str, lang_name: str) -> tuple[dict, list[float]]:
    prompt = VALIDATE_PROMPT_TEMPLATE.format(lang_name=lang_name, text=text)
    logger.info("claude validate start model=%s text=%r", ANTHROPIC_MODEL, text)
    raw_text, duration_ms = await _call(prompt)
    logger.info("claude validate done duration_ms=%.2f", duration_ms)
    try:
        result = _parse_json(raw_text)

        corrections = result.get("corrections")
        if isinstance(corrections, list):
            result["corrections"] = [c for c in corrections if c is not None] or None

        # Same degenerate-correction guard as ollama.validate
        if not result.get("is_valid") and isinstance(result.get("corrections"), list):
            def _norm(t: str) -> str:
                return re.sub(r"\s+", " ", t).strip().casefold()
            input_norm = _norm(text)
            result["corrections"] = (
                [c for c in result["corrections"] if _norm(c) != input_norm] or None
            )
            if result["corrections"] is None:
                result["is_valid"] = True

        return result, [duration_ms]
    except (json.JSONDecodeError, KeyError) as e:
        logger.error("claude validate parse error: %s | raw=%r", e, raw_text[:200])
        raise HTTPException(status_code=502, detail="Claude returned invalid output")
