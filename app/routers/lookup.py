from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.language import Language
from app.models.part_of_speech import PartOfSpeech
from app.schemas.language import LanguageResponse
from app.schemas.part_of_speech import PartOfSpeechResponse

router = APIRouter(tags=["Reference Data"])


@router.get("/languages", response_model=list[LanguageResponse])
def get_languages(db: Session = Depends(get_db)):
    return db.query(Language).order_by(Language.name).all()


@router.get("/parts-of-speech", response_model=list[PartOfSpeechResponse])
def get_parts_of_speech(db: Session = Depends(get_db)):
    return db.query(PartOfSpeech).order_by(PartOfSpeech.label).all()
