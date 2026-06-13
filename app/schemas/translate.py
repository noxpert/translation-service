from pydantic import BaseModel


class TranslateResponse(BaseModel):
    source_text: str
    target_text: str
    source_lang: str
    target_lang: str
    part_of_speech: str | None = None
    root_source: str | None = None
    root_target: str | None = None
    notes: str | None = None
