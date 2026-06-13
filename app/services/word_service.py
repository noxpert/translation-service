from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.language import Language
from app.models.part_of_speech import PartOfSpeech
from app.models.phrase import Phrase, PhraseTranslation
from app.models.source import Source
from app.models.word import Word, WordTranslation
from app.schemas.phrase import PhraseCreate, PhraseUpdate
from app.schemas.word import WordCreate, WordUpdate


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


def create_word(db: Session, data: WordCreate) -> Word:
    pos = resolve_part_of_speech(db, data.part_of_speech)
    source = resolve_or_create_source(db, data.source_name)

    word = Word(
        part_of_speech_id=pos.id if pos else None,
        source_id=source.id if source else None,
        notes=data.notes,
        context=data.context,
        is_verified=int(data.is_verified),
    )
    db.add(word)
    db.flush()  # populate word.id before inserting translations

    for t in data.translations:
        lang = resolve_language(db, t.language_code)
        db.add(WordTranslation(word_id=word.id, language_id=lang.id, text=t.text))

    db.commit()
    db.refresh(word)
    return word


def update_word(db: Session, word_id: int, data: WordUpdate) -> Word:
    word = db.query(Word).filter(Word.id == word_id).first()
    if word is None:
        raise HTTPException(status_code=404, detail="Word not found")

    if data.notes is not None:
        word.notes = data.notes
    if data.context is not None:
        word.context = data.context
    if data.is_verified is not None:
        word.is_verified = int(data.is_verified)
    if data.part_of_speech is not None:
        pos = resolve_part_of_speech(db, data.part_of_speech)
        word.part_of_speech_id = pos.id if pos else None
    if data.source_name is not None:
        source = resolve_or_create_source(db, data.source_name)
        word.source_id = source.id if source else None
    if data.translations is not None:
        # full replacement — partial translation updates are not supported
        db.query(WordTranslation).filter(WordTranslation.word_id == word.id).delete()
        for t in data.translations:
            lang = resolve_language(db, t.language_code)
            db.add(WordTranslation(word_id=word.id, language_id=lang.id, text=t.text))

    db.commit()
    db.refresh(word)
    return word


def delete_word(db: Session, word_id: int) -> None:
    word = db.query(Word).filter(Word.id == word_id).first()
    if word is None:
        raise HTTPException(status_code=404, detail="Word not found")
    db.delete(word)
    db.commit()


def create_phrase(db: Session, data: PhraseCreate) -> Phrase:
    source = resolve_or_create_source(db, data.source_name)

    phrase = Phrase(
        source_id=source.id if source else None,
        notes=data.notes,
        context=data.context,
    )
    db.add(phrase)
    db.flush()  # populate phrase.id before inserting translations

    for t in data.translations:
        lang = resolve_language(db, t.language_code)
        db.add(PhraseTranslation(phrase_id=phrase.id, language_id=lang.id, text=t.text))

    db.commit()
    db.refresh(phrase)
    return phrase


def update_phrase(db: Session, phrase_id: int, data: PhraseUpdate) -> Phrase:
    phrase = db.query(Phrase).filter(Phrase.id == phrase_id).first()
    if phrase is None:
        raise HTTPException(status_code=404, detail="Phrase not found")

    if data.notes is not None:
        phrase.notes = data.notes
    if data.context is not None:
        phrase.context = data.context
    if data.source_name is not None:
        source = resolve_or_create_source(db, data.source_name)
        phrase.source_id = source.id if source else None
    if data.translations is not None:
        # full replacement — partial translation updates are not supported
        db.query(PhraseTranslation).filter(PhraseTranslation.phrase_id == phrase.id).delete()
        for t in data.translations:
            lang = resolve_language(db, t.language_code)
            db.add(PhraseTranslation(phrase_id=phrase.id, language_id=lang.id, text=t.text))

    db.commit()
    db.refresh(phrase)
    return phrase


def delete_phrase(db: Session, phrase_id: int) -> None:
    phrase = db.query(Phrase).filter(Phrase.id == phrase_id).first()
    if phrase is None:
        raise HTTPException(status_code=404, detail="Phrase not found")
    db.delete(phrase)
    db.commit()


def search(
    db: Session, text: str, source_language_id: int, target_language_id: int
) -> tuple[list[Word], list[Phrase]]:
    pattern = f"%{text.lower()}%"

    word_ids_in_source = (
        db.query(WordTranslation.word_id)
        .filter(WordTranslation.language_id == source_language_id)
        .filter(func.lower(WordTranslation.text).like(pattern))
    )
    word_ids_in_target = (
        db.query(WordTranslation.word_id)
        .filter(WordTranslation.language_id == target_language_id)
    )
    words = (
        db.query(Word)
        .filter(Word.id.in_(word_ids_in_source))
        .filter(Word.id.in_(word_ids_in_target))
        .all()
    )

    phrase_ids_in_source = (
        db.query(PhraseTranslation.phrase_id)
        .filter(PhraseTranslation.language_id == source_language_id)
        .filter(func.lower(PhraseTranslation.text).like(pattern))
    )
    phrase_ids_in_target = (
        db.query(PhraseTranslation.phrase_id)
        .filter(PhraseTranslation.language_id == target_language_id)
    )
    phrases = (
        db.query(Phrase)
        .filter(Phrase.id.in_(phrase_ids_in_source))
        .filter(Phrase.id.in_(phrase_ids_in_target))
        .all()
    )

    return words, phrases
