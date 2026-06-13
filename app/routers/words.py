from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.word import WordCreate, WordResponse, WordUpdate
from app.services import word_service

router = APIRouter(tags=["Words"])


@router.post("/words", response_model=WordResponse, status_code=201)
def create_word(data: WordCreate, db: Session = Depends(get_db)):
    return word_service.create_word(db, data)


@router.patch("/words/{word_id}", response_model=WordResponse)
def update_word(word_id: int, data: WordUpdate, db: Session = Depends(get_db)):
    return word_service.update_word(db, word_id, data)


@router.delete("/words/{word_id}", status_code=204)
def delete_word(word_id: int, db: Session = Depends(get_db)):
    word_service.delete_word(db, word_id)
    return Response(status_code=204)
