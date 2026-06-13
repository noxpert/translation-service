from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class PhraseTranslationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    phrase_id: int
    language_id: int
    text: str
    created_at: datetime


class PhraseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_id: int | None = None
    notes: str | None = None
    context: str | None = None
    created_at: datetime
    translations: list[PhraseTranslationResponse] = []


class PhraseTranslationInput(BaseModel):
    language_code: str
    text: str


class PhraseCreate(BaseModel):
    translations: list[PhraseTranslationInput]
    notes: str | None = None
    context: str | None = None
    source_name: str | None = None

    @field_validator("translations")
    @classmethod
    def at_least_one_translation(
        cls, v: list[PhraseTranslationInput]
    ) -> list[PhraseTranslationInput]:
        if len(v) < 1:
            raise ValueError("At least one translation is required")
        return v


class PhraseUpdate(BaseModel):
    translations: list[PhraseTranslationInput] | None = None
    notes: str | None = None
    context: str | None = None
    source_name: str | None = None
