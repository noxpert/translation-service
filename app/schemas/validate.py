from pydantic import BaseModel


class ValidateRequest(BaseModel):
    text: str
    lang: str


class ValidateResponse(BaseModel):
    is_valid: bool
    text: str
    corrections: list[str] | None = None
    ollama_calls_ms: list[float]
