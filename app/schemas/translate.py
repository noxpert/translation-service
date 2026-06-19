from pydantic import BaseModel


class TranslateRequest(BaseModel):
    text: str
    source_lang: str
    target_lang: str


class TranslateResponse(BaseModel):
    source_text: str
    target_text: str
    source_lang: str
    target_lang: str
    part_of_speech: str | None = None
    root_source: str | None = None
    root_target: str | None = None
    synonyms: list[str] | None = None
    notes: str | None = None
    ollama_calls_ms: list[float]
