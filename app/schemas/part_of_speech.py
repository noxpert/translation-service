from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PartOfSpeechResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    label: str
    created_at: datetime
