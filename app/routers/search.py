from typing import cast

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.phrase import PhraseResponse
from app.schemas.search import SearchRequest, SearchResponse
from app.schemas.word import WordResponse
from app.services import word_service
from app.services.word_service import resolve_language

router = APIRouter(tags=["Search"])


@router.post("/search", response_model=SearchResponse)
def search(data: SearchRequest, db: Session = Depends(get_db)):
    source = resolve_language(db, data.source_lang)
    target = resolve_language(db, data.target_lang)
    words, phrases = word_service.search(db, data.text, cast(int, source.id), cast(int, target.id))
    return SearchResponse(
        words=[WordResponse.model_validate(w) for w in words],
        phrases=[PhraseResponse.model_validate(p) for p in phrases],
    )
