from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.search import SearchRequest, SearchResponse
from app.services import word_service
from app.services.word_service import resolve_language

router = APIRouter(tags=["Search"])


@router.post("/search", response_model=SearchResponse)
def search(data: SearchRequest, db: Session = Depends(get_db)):
    source = resolve_language(db, data.source_lang)
    target = resolve_language(db, data.target_lang)
    words, phrases = word_service.search(db, data.text, source.id, target.id)
    return SearchResponse(words=words, phrases=phrases)
