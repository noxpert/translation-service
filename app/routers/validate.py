from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.language import Language
from app.schemas.validate import ValidateRequest, ValidateResponse
from app.services import llm

router = APIRouter(tags=["Translation"])


@router.post("/validate", response_model=ValidateResponse)
async def validate_text(
    body: ValidateRequest,
    db: Session = Depends(get_db),
):
    lang = db.query(Language).filter(Language.code == body.lang).first()
    if lang is None:
        raise HTTPException(status_code=400, detail=f"Unknown language: {body.lang}")

    result, ollama_calls_ms = await llm.validate(body.text, lang.name)

    return ValidateResponse(
        is_valid=result.get("is_valid", False),
        text=body.text,
        corrections=result.get("corrections"),
        ollama_calls_ms=ollama_calls_ms,
    )
