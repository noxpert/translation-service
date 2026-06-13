from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.phrase import PhraseCreate, PhraseResponse, PhraseUpdate
from app.services import word_service

router = APIRouter(tags=["Phrases"])


@router.post("/phrases", response_model=PhraseResponse, status_code=201)
def create_phrase(data: PhraseCreate, db: Session = Depends(get_db)):
    return word_service.create_phrase(db, data)


@router.patch("/phrases/{phrase_id}", response_model=PhraseResponse)
def update_phrase(phrase_id: int, data: PhraseUpdate, db: Session = Depends(get_db)):
    return word_service.update_phrase(db, phrase_id, data)


@router.delete("/phrases/{phrase_id}", status_code=204)
def delete_phrase(phrase_id: int, db: Session = Depends(get_db)):
    word_service.delete_phrase(db, phrase_id)
    return Response(status_code=204)
