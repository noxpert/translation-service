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

# Greedy decoding: eliminates synonym swaps, re-punctuation, and inconsistent
# valid/invalid judgements that high temperature introduces.
DECODE_OPTIONS = {"temperature": 0, "top_p": 1, "repeat_penalty": 1.0}

VALIDATE_PROMPT_TEMPLATE = """You are a multilingual linguistics assistant and spelling checker.

Check whether the following text is correctly written in {lang_name}.
Consider spelling, grammar, diacritical marks, and natural usage.

IMPORTANT — diacritical marks are never optional:
- In Hungarian, á é í ó ö ő ú ü ű are completely different letters from a e i o u.
  Writing "u" when the correct letter is "ü", or "e" when it should be "é", is a spelling error.
  Treat any missing or substituted accent as an error, even if the word is otherwise recognisable.
- Apply the same strict rule for any language that uses diacritical marks.

IMPORTANT — Hungarian compound words:
Hungarian productively forms closed compounds by joining nouns/adjectives with no spaces
(e.g. katedraasztal, vasútállomás, természettudomány). Do NOT split a compound into separate
words and do NOT mark it invalid just because it is unfamiliar or long. A compound is valid
as long as it is correctly spelled with correct diacritics; only flag it when it contains an
actual letter/diacritic error, and when correcting keep it as one word.

Input text: "{text}"

Respond ONLY with a valid JSON object. No explanation, no markdown, no code fences.

The JSON must have exactly these fields:
{{
  "is_valid": <true if the text is correct, false if it contains any error>,
  "corrections": ["<corrected version>", "..."] or null
}}

Examples:
1. Valid fragment, lowercase, no period:
   Input "katedraasztalán" -> {{"is_valid": true, "corrections": null}}
2. Diacritic-only error, surgical fix, nothing else changed:
   Input "termesetrajzi" -> {{"is_valid": false, "corrections": ["természetrajzi"]}}
3. Correct archaic phrasing left untouched (no modernisation):
   Input "annak jeléül, hogy az a vegyület ... csakugyan zöldre festette"
     -> {{"is_valid": true, "corrections": null}}
4. Literary "s" (meaning "and") must NOT become "és" or gain a comma; fix only the
   actual character-level errors and copy EVERY word verbatim — including all words
   that follow the corrected word:
   Input "Az ablakok tárva-nyitva voltak a melleg napon s a fris szellő szárnyán berepult a muzsika a terembe."
     -> {{"is_valid": false, "corrections": ["Az ablakok tárva-nyitva voltak a meleg napon s a friss szellő szárnyán berepült a muzsika a terembe."]}}
   (Three fixes: "melleg"→"meleg", "fris"→"friss", "berepult"→"berepült";
    "s", "a muzsika", "a terembe" all copied verbatim — no word is ever omitted)

Rules:
- The input may be a single word, a phrase, a clause, or a full sentence. A fragment is NOT
  an error: do not mark text invalid merely because it starts lowercase, lacks final
  punctuation, or is not a complete sentence.
- Correctly-spelled archaic, literary, dialectal, or old-fashioned Hungarian is VALID. Only
  spelling, diacritic, and clear grammatical errors count. Never set is_valid to false just
  because more modern or more formal phrasing exists.
- If is_valid is true, corrections must be null
- If is_valid is false, provide 1 to 3 corrected versions of the full text in order of likelihood
- Corrections must be SURGICAL. Copy the input verbatim and change ONLY the specific characters
  that are misspelled (wrong letters, missing or wrong diacritics). The correction must contain
  every word from the input — never omit, add, or reorder any word. Preserve word order,
  capitalisation, punctuation, and conjunctions exactly. Do NOT substitute synonyms, do NOT
  modernise archaic words, do NOT change "s" to "és" or "melyről" to "amelyről", do NOT add or
  remove a leading capital letter, and do NOT add or remove commas unless a comma is itself
  unambiguously wrong. The correction should differ from the input at as few characters as
  possible.
- Return null for corrections if you are not confident about any correction
- Dropping one letter from a doubled (geminate) consonant always produces a different word or
  a non-word — it is NEVER a valid alternate spelling. Flag it as invalid regardless of any
  uncertainty. Do not apply the tie-breaker below to geminate reductions.
    megcsinálata (one 'l' dropped from megcsinálta) → is_valid: false
- If you are uncertain whether a word, compound, or construction is valid, set is_valid to true
  and corrections to null. Only set is_valid to false when you are confident there is a genuine
  spelling error or diacritical mistake. Err on the side of accepting correct text rather than
  over-correcting valid text."""

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
- root_source: the dictionary/lemma form of the input word — only set this if the
  input is inflected or conjugated, otherwise null. Three rules govern this:

  RULE A — Uninflected derivational forms: if the word's ONLY morphology is a
  derivational suffix (not also conjugated or declined), that derived form IS the
  base — set root_source to null.
    természetrajzi (természetrajz + relational-adj -i, no case suffix) → null
    boldogság (boldog + -ság abstract-noun suffix, no case suffix) → null

  RULE B — Inflected/conjugated words: if the word carries any inflectional suffix
  (case ending, conjugation, possessive agreement), set root_source to the lemma —
  even when derivational morphology is also present.
    For VERBS the lemma is ALWAYS the infinitive ending in -ni/-ani/-eni. NEVER use
    the bare verb stem — always the full infinitive.
      látom  → látni   (NOT "lát")
      látok  → látni   (NOT "lát")
      olvastatja → olvastatni  (causative -tat + 3sg conjugation → infinitive of derived verb)
      járogat    → járogatni   (frequentative -gat + 3sg conjugation → infinitive of derived verb)
    For NOUNS/ADJECTIVES remove inflectional suffixes AND comparative/superlative
    morphology to reach the bare positive-form noun/adjective, including the full
    compound when the input is a compound noun.
      autóba → autó
      házban → ház
      katedraasztalán → katedraasztal  (compound noun + -án inessive suffix)
      legszebbjeit → szép  (leg- superlative + szép→szebb + -bb + -jei + -t; root is the
                            bare positive adjective, NOT "legszép" or "legszebb")

  RULE C — Nouns derived from verbs: use the noun as root, not the underlying verb.

- root_target: the {target_lang_name} translation of root_source, or null if root_source is null
- notes: mention conjugation pattern, suffix meaning, or alternate meanings if relevant.
  For Hungarian verb forms, notes MUST state whether the conjugation is definite
  (definite-object agreement) or indefinite — this distinction is invisible in English.
  If the input is a homograph (same form, multiple meanings or word classes), notes is
  REQUIRED: explain both readings and state which this translation assumes.
    vár: could be noun "castle/fort" or verb "to wait" — notes must name both.
  Hungarian 3rd-person possessive suffixes (-a/-e/-ja/-je and plural forms) are
  gender-neutral. Use "his/her" for singular human possessors, "their" for plural or
  unspecified human possessors, and "its" only for clearly non-human possessors.
    házaiban → "in their houses" or "in his/her houses"  (NOT "in its houses")
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
                    "format": "json",
                    "options": DECODE_OPTIONS,
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
                    "format": "json",
                    "options": DECODE_OPTIONS,
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
                    "format": "json",
                    "options": DECODE_OPTIONS,
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

        # Guard: if the model says invalid but every correction equals the input,
        # it is self-contradicting — treat as valid.
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
        logger.error(f"Failed to parse Ollama response: {e}")
        raise HTTPException(
            status_code=502,
            detail="Ollama returned invalid output",
        )
