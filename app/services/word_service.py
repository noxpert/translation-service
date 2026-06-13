from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.language import Language
from app.models.part_of_speech import PartOfSpeech
from app.models.source import Source


def resolve_part_of_speech(db: Session, code: str | None) -> PartOfSpeech | None:
    """Look up a POS by code. Falls back to 'other' if not found."""
    if code is None:
        return None
    normalized = code.strip().lower()
    pos = db.query(PartOfSpeech).filter(PartOfSpeech.code == normalized).first()
    if pos is None:
        pos = db.query(PartOfSpeech).filter(PartOfSpeech.code == "other").first()
    return pos


def resolve_language(db: Session, code: str) -> Language:
    """Look up a language by code. Raises 400 if not found."""
    lang = db.query(Language).filter(Language.code == code).first()
    if lang is None:
        raise HTTPException(status_code=400, detail=f"Unknown language: {code}")
    return lang


def resolve_or_create_source(db: Session, name: str | None) -> Source | None:
    """Look up a source by name, creating it if it doesn't exist."""
    if name is None:
        return None
    source = db.query(Source).filter(Source.name == name).first()
    if source is None:
        source = Source(name=name)
        db.add(source)
        db.commit()
        db.refresh(source)
    return source
