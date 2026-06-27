import logging
import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.language import Language
from app.models.part_of_speech import PartOfSpeech
from app.schemas.translate import TranslateRequest, TranslateResponse
from app.services import llm

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Translation"])


@router.post("/translate", response_model=TranslateResponse)
async def translate_text(
    body: TranslateRequest,
    db: Session = Depends(get_db),
):
    text, source_lang, target_lang = body.text, body.source_lang, body.target_lang
    t_request = time.monotonic()
    logger.info("translate request text=%r src=%s tgt=%s", text, source_lang, target_lang)

    # Validate language codes
    source = db.query(Language).filter(Language.code == source_lang).first()
    if source is None:
        raise HTTPException(status_code=400, detail=f"Unknown source language: {source_lang}")

    target = db.query(Language).filter(Language.code == target_lang).first()
    if target is None:
        raise HTTPException(status_code=400, detail=f"Unknown target language: {target_lang}")

    # Call 1+2: Translate
    result, translate_timings = await llm.translate(text, source.name, target.name)
    ollama_calls_ms: dict[str, float] = {"translate": translate_timings[0]}

    # Normalize part_of_speech against the lookup table
    pos_value = result.get("part_of_speech")
    if pos_value is not None:
        normalized = pos_value.strip().lower()
        pos_row = db.query(PartOfSpeech).filter(PartOfSpeech.code == normalized).first()
        if pos_row is None:
            pos_value = "other"
        else:
            pos_value = pos_row.code

    # Call 3 (optional): Synonyms — only when a root form was identified
    synonyms = None
    if result.get("root_source") is not None:
        source_text = result.get("root_source", text)
        target_text = result.get("root_target", "")
        synonyms, syn_timings = await llm.get_synonyms(
            source_text, target_text, pos_value, source.name, target.name
        )
        ollama_calls_ms["synonyms"] = syn_timings[0]

    total_ms = round((time.monotonic() - t_request) * 1000, 2)
    logger.info("translate complete total_ms=%.2f calls=%s", total_ms, ollama_calls_ms)

    return TranslateResponse(
        source_text=result.get("source_text", text),
        target_text=result.get("target_text", ""),
        source_lang=source_lang,
        target_lang=target_lang,
        part_of_speech=pos_value,
        root_source=result.get("root_source"),
        root_target=result.get("root_target"),
        synonyms=synonyms,
        notes=result.get("notes"),
        ollama_calls_ms=ollama_calls_ms,
    )
