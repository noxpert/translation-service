from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class WordTranslationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    word_id: int
    language_id: int
    text: str
    created_at: datetime


class WordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    part_of_speech_id: int | None = None
    source_id: int | None = None
    notes: str | None = None
    context: str | None = None
    is_verified: int
    created_at: datetime
    translations: list[WordTranslationResponse] = []


class WordTranslationInput(BaseModel):
    language_code: str
    text: str


class WordCreate(BaseModel):
    translations: list[WordTranslationInput]
    part_of_speech: str
    notes: str | None = None
    context: str | None = None
    source_name: str | None = None
    is_verified: bool = False

    @field_validator("translations")
    @classmethod
    def at_least_one_translation(cls, v: list[WordTranslationInput]) -> list[WordTranslationInput]:
        if len(v) < 1:
            raise ValueError("At least one translation is required")
        return v


class WordUpdate(BaseModel):
    translations: list[WordTranslationInput] | None = None
    part_of_speech: str | None = None
    notes: str | None = None
    context: str | None = None
    source_name: str | None = None
    is_verified: bool | None = None
