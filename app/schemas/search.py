from pydantic import BaseModel

from app.schemas.phrase import PhraseResponse
from app.schemas.word import WordResponse


class SearchRequest(BaseModel):
    text: str
    source_lang: str
    target_lang: str


class SearchResponse(BaseModel):
    words: list[WordResponse]
    phrases: list[PhraseResponse]
